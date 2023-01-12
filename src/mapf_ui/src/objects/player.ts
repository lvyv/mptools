import { Bullet } from './bullet';
import { IImageConstructor } from '../interfaces/image.interface';

export class Player extends Phaser.GameObjects.Image {
  body: Phaser.Physics.Arcade.Body;
  // variables
  private health: number;
  private lastShoot: number;
  private speed: number;

  // children
  // private agvbody: Phaser.GameObjects.Sprite;
  // private barrel: Phaser.GameObjects.Image;
  private lifeBar: Phaser.GameObjects.Graphics;

  // game objects
  private bullets: Phaser.GameObjects.Group;

  // input
  private cursors: Phaser.Types.Input.Keyboard.CursorKeys;
  private rotateKeyLeft: Phaser.Input.Keyboard.Key;
  private rotateKeyRight: Phaser.Input.Keyboard.Key;
  private shootingKey: Phaser.Input.Keyboard.Key;

  public getBullets(): Phaser.GameObjects.Group {
    return this.bullets;
  }

  constructor(aParams: IImageConstructor) {
    super(aParams.scene, aParams.x, aParams.y, aParams.texture, aParams.frame);
    this.initImage();
    this.scene.add.existing(this);
  }
  private initImage() {
    // variables
    this.health = 1;
    this.lastShoot = 0;
    this.speed = 300;

    // image
    this.setOrigin(0.5, 0.5);
    this.setDepth(10);
    this.angle = 180;

    // this.barrel = this.scene.add.image(this.x, this.y, 'barrelBlue');
    // this.barrel.setOrigin(0.5, 1);
    // this.barrel.setDepth(1);
    // this.barrel.angle = 180;

    this.lifeBar = this.scene.add.graphics();
    this.redrawLifebar();

    // game objects
    this.bullets = this.scene.add.group({
      /*classType: Bullet,*/
      active: true,
      maxSize: 10,
      runChildUpdate: true
    });

    // this.agvbody = this.scene.add.sprite(this.x, this.y, "atlas", "agv/down/0001");
    const anims = this.scene.anims;
    anims.create({
      key: "agv-down",
      frames: anims.generateFrameNames("atlas", {
        prefix: "agv/down/",
        start: 1,
        end: 4,
        zeroPad: 4,
      }),
      frameRate: 10,
      repeat: -1,
    });
    anims.create({
      key: "agv-left",
      frames: anims.generateFrameNames("atlas", {
        prefix: "agv/left/",
        start: 1,
        end: 4,
        zeroPad: 4,
      }),
      frameRate: 10,
      repeat: -1,
    });
    anims.create({
      key: "agv-right",
      frames: anims.generateFrameNames("atlas", {
        prefix: "agv/right/",
        start: 1,
        end: 4,
        zeroPad: 4,
      }),
      frameRate: 10,
      repeat: -1,
    });
    anims.create({
      key: "agv-up",
      frames: anims.generateFrameNames("atlas", {
        prefix: "agv/up/",
        start: 1,
        end: 4,
        zeroPad: 4,
      }),
      frameRate: 10,
      repeat: -1,
    });
    // this.agvbody.anims.play('agv-up',true)
    // input
    this.cursors = this.scene.input.keyboard.createCursorKeys();
    this.rotateKeyLeft = this.scene.input.keyboard.addKey(
      Phaser.Input.Keyboard.KeyCodes.A
    );
    this.rotateKeyRight = this.scene.input.keyboard.addKey(
      Phaser.Input.Keyboard.KeyCodes.D
    );
    this.shootingKey = this.scene.input.keyboard.addKey(
      Phaser.Input.Keyboard.KeyCodes.SPACE
    );
    

    // physics
    this.scene.physics.world.enable(this);

  }

  update(): void {
    if (this.active) {
      // this.agvbody.x = this.x;
      // this.agvbody.y = this.y;
      // this.barrel.x = this.x;
      // this.barrel.y = this.y;
      this.lifeBar.x = this.x;
      this.lifeBar.y = this.y;
      this.handleInput();
      // this.handleShooting();
    } else {
      this.destroy();
      // this.barrel.destroy();
      this.lifeBar.destroy();
    }
  }

  private handleInput() {
    // move tank forward
    // small corrections with (- MATH.PI / 2) to align tank correctly
    if (this.cursors.up.isDown) {
      /* 给出角度与大小，求出速度矢量 */
      this.scene.physics.velocityFromRotation(
        this.rotation - Math.PI / 2,
        this.speed,
        this.body.velocity
      );
    } else if (this.cursors.down.isDown) {
      this.scene.physics.velocityFromRotation(
        this.rotation - Math.PI / 2,
        -this.speed,
        this.body.velocity
      );
    } else {
      this.body.setVelocity(0, 0);
    }

    // rotate tank
    if (this.cursors.left.isDown) {
      this.rotation -= 0.02;
    } else if (this.cursors.right.isDown) {
      this.rotation += 0.02;
    }

    // // rotate barrel
    // if (this.rotateKeyLeft.isDown) {
    //   this.barrel.rotation -= 0.05;
    // } else if (this.rotateKeyRight.isDown) {
    //   this.barrel.rotation += 0.05;
    // }

    //show animations of the sprite
    // if(this.cursors.left.isDown) this.agvbody.anims.play('agv-left', true);
    // else if(this.cursors.right.isDown) this.agvbody.anims.play('agv-right', true);
    // else if(this.cursors.up.isDown) this.agvbody.anims.play('agv-up', true);
    // else if(this.cursors.down.isDown) this.agvbody.anims.play('agv-down',true);
    // else this.agvbody.anims.stop();
  }

  // private handleShooting(): void {
  //   if (this.shootingKey.isDown && this.scene.time.now > this.lastShoot) {
  //     this.scene.cameras.main.shake(20, 0.005);
  //     this.scene.tweens.add({
  //       targets: this,
  //       props: { alpha: 0.8 },
  //       delay: 0,
  //       duration: 5,
  //       ease: 'Power1',
  //       easeParams: null,
  //       hold: 0,
  //       repeat: 0,
  //       repeatDelay: 0,
  //       yoyo: true,
  //       paused: false
  //     });

  //     if (this.bullets.getLength() < 10) {
  //       this.bullets.add(
  //         new Bullet({
  //           scene: this.scene,
  //           rotation: this.barrel.rotation,
  //           x: this.barrel.x,
  //           y: this.barrel.y,
  //           texture: 'bulletBlue'
  //         })
  //       );

  //       this.lastShoot = this.scene.time.now + 80;
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
      this.scene.scene.start('MenuScene');
    }
  }
}
