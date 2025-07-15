import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：めじろうや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：めじろうSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（めじろう）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        めじろう画像Surfaceを生成する
        引数2 xy：めじろう画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/mejirou.png"), 0, 0.05)
        img = pg.transform.flip(img0, True, False)  # デフォルトのめじろう
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        めじろう画像を切り替え，画面に転送する
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/mejirou.png"), 0, 0.05)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてめじろうを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird,angle:float | None = None):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つめじろう
        """
        super().__init__()
        if angle is None:
            dx,dy = bird.dire
            angle = math.degrees(math.atan2(-dy, dx))
            self.vx, self.vy = dx,dy
        else:
            self.vx = math.cos(math.radians(angle))
            self.vy = -math.sin(math.radians(angle))
        self.image = pg.transform.rotozoom(pg.image.load("fig/beam.png"),angle,1.0)
        self.rect = self.image.get_rect()
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.speed = 12
        

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/{i}.png") for i in range(0, 5)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 2)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class NeoBeam:
    def __init__(self, bird: Bird, num: int = 5):
        """
        bird: こうかとん（ビームを撃つやつ）
        num: 発射するビームの数（奇数推奨）
        """
        self.bird = bird
        self.num = max(1,num) #ビームを最低でも一本出し、numの数に応じて最大本数が変わる

    def gen_beams(self) -> list[Beam]:
        """
        ビーム角度をずらしながら Beam インスタンスをリストで返す
        """

        step = 360 / self.num 
        return [Beam(self.bird, angle) 
                for angle in (i * step for i in range(self.num))] # i を 0〜(self.num-1) まで増やし、step をかけて angle を求める

class Skill:
    """
    敵を倒すとスキルゲージがたまり、拡散ビームを打つ
    """
    def __init__(self,max_value: int = 5):
        self.value = 0 
        self.max = max_value #最大スキルポイント
        self.bar_area = pg.Rect(WIDTH-250,HEIGHT-40,200,15) # スキルゲージを表示するための長方形
        self.font = pg.font.Font(None,30) #スキルゲージの文字フォント

    def add(self,n:int = 1): #増やすスキルポイント 敵を倒した際のスキルポイント
        self.value = min(self.max,self.value + n) # 最大値を超えないように加算
    
    def ready(self) -> bool:
        return self.value >= self.max # スキルを発動できる状態か（満タンならTrue）
    
    def consume(self):
        self.value = 0 # スキルを使った際スキルポイントを0にする

    def draw(self, screen:pg.surface): # スキルゲージを画面に描画する処理
        pg.draw.rect(screen, (255,0,0),self.bar_area,2) # ゲージの枠（レッド）を描く
        inner = self.bar_area.copy() # 枠と同じサイズの中身を作成
        inner.width = self.bar_area.width*self.value/self.max # ゲージの中身の長さを現在の値に応じて設定
        pg.draw.rect(screen,(255,215,0),inner) # ゲージの中身の色を描画
        txt = self.font.render(f"skill{self.value}/{self.max}" ,True,(255,215,0)) # ゲージ上部に表示するテキストを描画（例：skill 3/5）
        screen.blit(txt,(self.bar_area.x,self.bar_area.y -22)) # テキストをゲージの上に表示


def main():
    pg.display.set_caption("詰む積む")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/haikei.png")
    score = Score()
    skill = Skill()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN: # スペースキーが押されたら
                if event.key == pg.K_RETURN and  skill.ready(): # スキルゲージが満タンなら Enterキーで発動
                    for b in NeoBeam(bird, num = 32).gen_beams():   # 32方向にビームを放つ
                        beams.add(b) # 各ビームをビームグループに追加
                    skill.consume() # スキルゲージを消費
                elif event.key == pg.K_SPACE: #スキルゲージがたまっていなければ
                    beams.add(Beam(bird)) # 通常ビームを1発だけ追加

        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            skill.add()
            bird.change_img(6, screen)  # めじろう喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # めじろうと衝突した爆弾リスト
            bird.change_img(8, screen)  # めじろう悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        skill.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
