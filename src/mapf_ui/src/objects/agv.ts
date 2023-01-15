import { Bullet } from './bullet';
import { IFollowerConstructor } from '../interfaces/follower.interface';

export class Agv extends Phaser.GameObjects.PathFollower {
  body: Phaser.Physics.Arcade.Body;

  // variables
  private health: number;
  private lastShoot: number;
  private speed: number;

  // children
  // private barrel: Phaser.GameObjects.Image;
  private lifeBar: Phaser.GameObjects.Graphics;

  // game objects
  private bullets: Phaser.GameObjects.Group;

  // public getBarrel(): Phaser.GameObjects.Image {
  //   return this.barrel;
  // }

  public getBullets(): Phaser.GameObjects.Group {
    return this.bullets;
  }

  constructor(aParams: IFollowerConstructor) {
    super(aParams.scene, aParams.path, aParams.x, aParams.y, aParams.texture, aParams.frame);
    if (typeof aParams.speed !== 'undefined') this.speed = aParams.speed;
    else this.speed = 5;
    this.initContainer();
    this.scene.add.existing(this);
    //duration很重要，需要根据路径和速度进行计算
    if (aParams.path) {
      let arr = aParams.path.getCurveLengths();
      let sLen = 0;
      arr.forEach(function (val, idx, arr) { sLen += val; }, 0);
      this.startFollow({
        positionOnPath: true,
        duration: sLen / this.speed,
        yoyo: false,
        repeat: 1,
        rotateToPath: true,
        // verticalAdjust: true
      });
    }
  }

  private initContainer() {
    // variables
    this.health = 1;
    this.lastShoot = 0;
    // this.speed = 100;

    // image
    this.setDepth(10);

    // this.barrel = this.scene.add.image(0, 0, 'barrelRed');
    // this.barrel.setOrigin(0.5, 1);
    // this.barrel.setDepth(1);

    this.lifeBar = this.scene.add.graphics();
    this.redrawLifebar();

    // game objects
    this.bullets = this.scene.add.group({
      /*classType: Bullet,*/
      active: true,
      maxSize: 10,
      runChildUpdate: true
    });

    // tweens
    // this.scene.tweens.add({
    //   targets: this,
    //   props: { y: this.y - 200 },
    //   delay: 0,
    //   duration: 2000,
    //   ease: 'Linear',
    //   easeParams: null,
    //   hold: 0,
    //   repeat: -1,
    //   repeatDelay: 0,
    //   yoyo: true
    // });

    // physics
    this.scene.physics.world.enable(this);
  }

  update(): void {
    if (this.active) {
      // this.barrel.x = this.x;
      // this.barrel.y = this.y;
      this.lifeBar.x = this.x;
      this.lifeBar.y = this.y;
      // this.handleShooting(); // not allowed shooting for debug reason.
    } else {
      this.destroy();
      // this.barrel.destroy();
      this.lifeBar.destroy();
    }
  }

  // private handleShooting(): void {
  //   if (this.scene.time.now > this.lastShoot) {
  //     if (this.bullets.getLength() < 10) {
  //       this.bullets.add(
  //         new Bullet({
  //           scene: this.scene,
  //           rotation: this.barrel.rotation,
  //           x: this.barrel.x,
  //           y: this.barrel.y,
  //           texture: 'bulletRed'
  //         })
  //       );

  //       this.lastShoot = this.scene.time.now + 400;
  //     }
  //   }
  // }

  private redrawLifebar(): void {
    this.lifeBar.clear();
    this.lifeBar.fillStyle(0x0cad00, 1);
    this.lifeBar.fillRect(
      -this.width / 2,
      this.height / 2,
      this.width * this.health,
      15
    );
    this.lifeBar.lineStyle(2, 0xffffff);
    this.lifeBar.strokeRect(-this.width / 2, this.height / 2, this.width, 15);
    this.lifeBar.setDepth(11);
  }

  public updateHealth(): void {
    if (this.health > 0) {
      this.health -= 0.05;
      this.redrawLifebar();
    } else {
      this.health = 0;
      this.active = false;
    }
  }

  public getSpeed(): number {
    return this.speed;
  }
}
