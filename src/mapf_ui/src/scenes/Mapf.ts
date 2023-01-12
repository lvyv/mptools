import Phaser from 'phaser'
import { SceneBusKeys } from '~/consts/SceneKeys';
import { Player } from '../objects/player';
import { Enemy } from '../objects/enemy';
import { Agv } from '../objects/agv'
import { Obstacle } from '../objects/obstacles/obstacle';
import { FBDInputHandler } from '../interfaces/FBDInputHandler';

/* keyboard input mapping */
const INPUT_KEYS_MAPPING = {
  'zoomIn': [
    Phaser.Input.Keyboard.KeyCodes.Z,
  ],
  'zoomOut': [
    Phaser.Input.Keyboard.KeyCodes.X,
  ],
  'exitToMenu': [
    Phaser.Input.Keyboard.KeyCodes.ESC,
  ],
}


export default class Mapf extends Phaser.Scene {
  private layer: Phaser.Tilemaps.TilemapLayer;

  private player: Player;
  private enemies: Phaser.GameObjects.Group;
  private agvs: Phaser.GameObjects.Group;
  private obstacles: Phaser.GameObjects.Group;
  private zxkmap: Phaser.Tilemaps.Tilemap;
  private gfx: Phaser.GameObjects.Graphics;
  private parent!: Phaser.GameObjects.Zone;
  private inputHandler: FBDInputHandler;
  private speed:number;
  public static WIDTH = 1048
  public static HEIGHT = 775
  public bg?: any

  constructor(handle, parent) {
    super(handle);
    this.parent = parent;
    this.speed = 6;
  }

  create() {
    this.bg = this.add.image(0, 0, 'cad').setOrigin(0).setAlpha(0.8)

    this.zxkmap = this.make.tilemap({ key: 'zxkmap2' });
    // let ts1 = this.zxkmap.addTilesetImage('roads', 'roads');
    let ts2 = this.zxkmap.addTilesetImage('path-tile-set', 'path-tile-set');

    const worldLayer = this.zxkmap.createLayer("path", ts2, 0, 0);
    // const cadlayer = this.zxkmap.createLayer('base', 'cad')
    // worldLayer.setCollisionByProperty({ collides: true });

    this.inputHandler = new FBDInputHandler(this, INPUT_KEYS_MAPPING);

    this.obstacles = this.add.group({
      /*classType: Obstacle,*/
      runChildUpdate: true
    });

    this.enemies = this.add.group({
      /*classType: Enemy*/
    });

    this.agvs = this.add.group({
      /*classType: Agv*/
    });
    this.convertObjects();

    let vsp = 200
    this.bg.setInteractive(new Phaser.Geom.Rectangle(0, vsp, this.zxkmap.widthInPixels, this.zxkmap.heightInPixels - vsp), Phaser.Geom.Rectangle.Contains)
    this.bg.on('pointerdown', (pointer) => {
      // console.log(pointer.worldX, pointer.worldY)
      this.registry.set(SceneBusKeys.TopicTaskSet, { 'x': pointer.worldX / 8, 'y': pointer.worldY / 8 }) //FIXME 写死的块为8像素

    }, this)

    this.registry.events.on(SceneBusKeys.BusDataChange, this.updateData, this)

    // collider layer and obstacles
    this.physics.add.collider(this.player, this.layer);
    this.physics.add.collider(this.player, this.obstacles);
    this.physics.add.collider(this.player, this.enemies);

    // set viewpoint
    this.cameras.main.startFollow(this.player);
    let cam = this.cameras.main;
    // cam.setBounds(0, 0, this.zxkmap.widthInPixels, this.zxkmap.heightInPixels);
    cam.setBounds(0, 0, this.zxkmap.widthInPixels, this.zxkmap.heightInPixels);
    let ratio = this.zxkmap.widthInPixels / this.zxkmap.heightInPixels
    cam.setViewport(this.parent.x, this.parent.y, Mapf.HEIGHT * ratio + 40, Mapf.HEIGHT);
    cam.zoomTo(0.22, 500);
    this.physics.world.setBounds(0, 0, this.zxkmap.widthInPixels, this.zxkmap.heightInPixels);
  }

  update(time, delta) {
    this.player.update();
    // agvs redraw
    this.agvs.children.each((agv: Enemy) => {
      agv.update();
    }, this);

    // player as a detector
    let closest = this.physics.closest(this.player) as Phaser.Physics.Arcade.Body;

    // map zoom
    if (this.inputHandler.isJustDown('zoomIn')) {
      // zoomIn
      let cam = this.cameras.main;
      cam.zoomTo(1, 500);
    }
    if (this.inputHandler.isJustDown('zoomOut')) {
      // zoomOut
      let cam = this.cameras.main;
      cam.zoomTo(0.22, 500);
    }
    if (this.inputHandler.isJustDown('exitToMenu')) {
      // backToMenu
      this.scene.start('MenuScene');
    }
  }

  refresh() {
    this.cameras.main.setPosition(this.parent.x, this.parent.y);
    this.scene.bringToTop();
  }

  updateData(parent, key, data) {
    switch (key) {
      case SceneBusKeys.TopicMAPFCall:
        // call rest api to get mapf solution
        console.log(data)
        // draw path
        this.gfx = this.add.graphics();
        this.pathManager(this.cache, this.physics, this.agvs, this.gfx);
      default:
        break

    }
  }
  /* instantialize objects in the map */
  private convertObjects(): void {
    // find the object layer in the tilemap named 'objects'
    const objects = this.zxkmap.getObjectLayer('objects').objects as any[];

    objects.forEach((object) => {
      let udfProps = object['properties']
      if (udfProps) {
        udfProps.forEach((prop: any) => {
          if (prop.name === 'type' && prop.value === 'player') {
            this.player = new Player({
              scene: this,
              x: object.x,
              y: object.y,
              texture: 'tankBlue',
              // texture: 'atlas',
              // frame: 'agv/up/0001'
            });
          } else if (prop.name === 'type' && prop.value === 'camera') {
            let enemy = new Enemy({
              scene: this,
              x: object.x,
              y: object.y,
              texture: 'tankBlue'
            });
            this.enemies.add(enemy);
            // enemy.body.setFriction(1);
          } else if (prop.name === 'type' && prop.value === 'agv') {
            let agv = new Agv({
              scene: this,
              path: null,
              x: object.x,
              y: object.y,
              texture: 'atlas',
              frame: 'agv/right/0001',
              speed: 40
            });
            agv.setScale(.5);
            this.agvs.add(agv);
          } else {
            let obstacle = new Obstacle({
              scene: this,
              x: object.x,
              y: object.y - 40,
              texture: object.type
            });

            this.obstacles.add(obstacle);
          }
        });
      }
    });
  }

  pathManager(jsoncache: any, physics: Phaser.Physics.Arcade.ArcadePhysics, agvs: Phaser.GameObjects.Group, graphics: Phaser.GameObjects.Graphics) {
    // jsoncache保存的载入json是后台生成路径，直接生成path路径到dist文件
    // 此处解析文件，得到所有求出的路径
    let mapfs = jsoncache.json.get('pathData');
    let keys = Object.keys(mapfs);
    keys.forEach((val, idx, karr) => {
      let pts = mapfs[val];
      // find the nearest agv to the start point of the path
      let closest = physics.closest({ x: pts[0][0], y: pts[0][1] }, agvs.getChildren()) as Phaser.Physics.Arcade.Body;
      let path = new Phaser.Curves.Path(closest.x, closest.y);
      for (let iii = 1; iii < pts.length; iii++) {
        // let ind = getRand(0, pts.length);
        let cpt = pts[iii];
        path.lineTo(cpt[0], cpt[1]);
      }
  
      //对每条路径，计算总长度
      let arr = path.getCurveLengths();
      let sLen = 0;
      arr.forEach(function (val, idx, arr) { sLen += val; }, 0);
  
      let agv = closest as unknown as Agv;
      agv.setPath(path);
      path.getCurveLengths();
      agv.startFollow({
        positionOnPath: true,
        duration: sLen / agv.getSpeed(),
        yoyo: false,
        repeat: -1,
        rotateToPath: true,
        // verticalAdjust: true
      });
  
      // draw path line
      if (graphics) {
        graphics.lineStyle(6, 0x0000ff, 1);
        path.draw(graphics, 64);
      }
  
    }, 0);
  
    // return path;
    // return new Phaser.Curves.Path(obj.x, obj.y).circleTo(200);
  }
}
