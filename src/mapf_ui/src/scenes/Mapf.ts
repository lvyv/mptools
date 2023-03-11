import Phaser from 'phaser'
import { SceneBusKeys } from '~/consts/SceneKeys'
import { RestUri } from '~/consts/UiLabels'
import { Player } from '../objects/player'
import { Enemy } from '../objects/enemy'
import { Agv } from '../objects/agv'
import { Obstacle } from '../objects/obstacles/obstacle'
import { FBDInputHandler } from '../interfaces/FBDInputHandler'
import TextureKeys from '~/consts/TextureKeys'
import axios from 'axios'

/* keyboard input mapping */
const INPUT_KEYS_MAPPING = {
  'zoomIn': [
    Phaser.Input.Keyboard.KeyCodes.Z,
  ],
  'zoomOut': [
    Phaser.Input.Keyboard.KeyCodes.X,
  ],
  'zoomOne' : [
    Phaser.Input.Keyboard.KeyCodes.ONE, // move camera to p1
  ],
  'zoomTwo' : [
    Phaser.Input.Keyboard.KeyCodes.TWO, // move camera to p2
  ],
  'zoomThree' : [
    Phaser.Input.Keyboard.KeyCodes.THREE,// move camera to p3
  ],
  'zoomZero' : [
    Phaser.Input.Keyboard.KeyCodes.ZERO,// camera start follow player
  ],
  'exitToMenu': [
    Phaser.Input.Keyboard.KeyCodes.ESC,
  ],
}

const SPEEDFACTOR = 5

export default class Mapf extends Phaser.Scene {
  private layer!: Phaser.Tilemaps.TilemapLayer

  private player!: Player
  private enemies!: Phaser.GameObjects.Group
  private agvs!: Phaser.GameObjects.Group
  private obstacles!: Phaser.GameObjects.Group
  private zxkmap!: Phaser.Tilemaps.Tilemap
  private gfx!: Phaser.GameObjects.Graphics
  private parent!: Phaser.GameObjects.Zone;
  private inputHandler!: FBDInputHandler
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
    this.bg = this.add.image(0, 0, TextureKeys.Cad).setOrigin(0).setAlpha(0.8)

    this.zxkmap = this.make.tilemap({ key: TextureKeys.ZxkMap});
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
    // let ratio = this.zxkmap.widthInPixels / this.zxkmap.heightInPixels
    // cam.setViewport(this.parent.x, this.parent.y, Mapf.HEIGHT * ratio + 40, Mapf.HEIGHT);
    this.physics.world.setBounds(0, 0, this.zxkmap.widthInPixels, this.zxkmap.heightInPixels);
    cam.zoomTo(0.22, 500);
  }

  private speedController = 0
  update(time, delta) {
    this.player.update()
    this.speedController ++
    // 设置速度
    if(this.speedController % SPEEDFACTOR == 0) {
      this.agvs.children.each((agv: Agv) => {
        agv.update(this);
      }, this);
    }
    // player as a detector
    // let closest = this.physics.closest(this.player) as Phaser.Physics.Arcade.Body;
    let cam = this.cameras.main;
    // map zoom
    if (this.inputHandler.isJustDown('zoomIn')) {
      // zoomIn
      cam.zoomTo(1, 500);
    }
    if (this.inputHandler.isJustDown('zoomOut')) {
      // zoomOut
      cam.zoomTo(0.22, 500);
    }
    if (this.inputHandler.isJustDown('zoomOne')) {
      cam.stopFollow()
      cam.pan(1890,1740, 1000)
    }
    if (this.inputHandler.isJustDown('zoomTwo')) {
      cam.stopFollow()
      cam.pan(4430,1460, 1000)
    }
    if (this.inputHandler.isJustDown('zoomThree')) {
      cam.stopFollow()
      cam.pan(4400, 2250, 1000)
    }
    if (this.inputHandler.isJustDown('zoomZero')) {
      cam.startFollow(this.player)
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
        // console.log(data)
        // draw path
        this.gfx = this.add.graphics();
        this.pathManager(RestUri.Mapf_Uri, data, this.physics, this.agvs, this.gfx);
        break
      case SceneBusKeys.SetPhase:
        let agvs = this.agvs.getChildren()
        agvs.forEach(val=>{
          let agv = val as Agv
          agv.setToPhaseStartPos()
        })
        break
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

  /*
   目前的规划逻辑是用于演示任务，在实际的工程应用中，还需要实现滚动规划，就是规划路径是基于前一个执行规划中添加新规划任务
   对于用户点选的起点和终点，实际执行了两次路径规划，第一次规划是从任务起点到终点同时开始动作，但为了达到这个效果，还需要调度库区车辆从不同位置来到各自任务的起点
   所以需要规划各个AGV从驻车点出发，到达出发位置等待，一起按第一次规划路径行动
  */
  async pathManager(rest: string, tasks: string, physics: Phaser.Physics.Arcade.ArcadePhysics, agvs: Phaser.GameObjects.Group, graphics: Phaser.GameObjects.Graphics) {
    // 1.此处调用后端REST接口，求得所有任务的第一次规划路径
    let res = await axios.get(rest, { params: { map_name: 'zxk-640x440.map', tasks: tasks, alg_name: 'cbs' } })
    let mapfs = res.data.reply.result
    let keys = Object.keys(mapfs);
    // 设置一个数组保存召集AGV车任务的起始点
    let callAgvTasks: string[]=[]
    // 循环为每条路径分配AGV，分配之前要把所有AGV车路径和任务清空
    let targets = agvs.getChildren()
    targets.forEach((val) => {  // 任务清空
      let aitem = val as Agv
      aitem.clearTask()
    })
    keys.forEach((val) => {
      let pts = mapfs[val];
      // 寻找最靠近的AGV
      let closest = physics.closest({ x: pts[0][0], y: pts[0][1] }, targets) as Agv
      // 为该车分配任务号，比如pts0，并添加任务包含的路径
      closest.assignTaskID(val)
      closest.appendTaskPath(pts)
      // 找到最靠近的AGV，当一台AGV被占用后，将其移除，在新任务起点与移除车最近的情况下，让其它车被新分配
      targets = targets.filter(obj => obj !== closest)
      // '[{"s": [475, 168],"e": [509, 255]},   {"s": [359, 242],"e": [229, 328]}]'
      let agvX = closest.x, agvY = closest.y
      let callAgv = `{"s": [${Math.round(agvX/8)}, ${Math.round(agvY/8)}], "e": [${Math.round(pts[0][0]/8)}, ${Math.round(pts[0][1]/8)}]}`
      callAgvTasks.push(callAgv)
    }, this)

    // 2.此处调用后端REST接口，求得驻车点到任务起点的第二次规划路径
    let sCallAgvTasks = '[' + callAgvTasks.join(',') + ']'
    let res2 = await axios.get(rest, { params: { map_name: 'zxk-640x440.map', tasks: sCallAgvTasks, alg_name: 'cbs' } })
    let mapfs2 = res2.data.reply.result
    keys = Object.keys(mapfs2)  //mapfs和mapfs2应该是由统一的pts0,pts1标识
    // 第二次规划路径要添加到原来的分配一次规划路径对应的AGV上
    let agvitems = agvs.getChildren()
    keys.forEach((val) => {
      agvitems.forEach(item=>{
          let agvForNewPath = item as Agv
          if (agvForNewPath.checkTaskID(val)) {
            agvForNewPath.appendTaskPath(mapfs2[val])
          }
      })
    }, this)

    // 3.生成路径规划
    agvitems.forEach(item=>{  //每个AGV车
      let aitem = item as Agv
      if(aitem.getAgvTaskID() != '') {
        let paths = aitem.getAgvTaskPaths()
        let path
        paths.forEach((pitem,ind)=>{  //车辆分配任务的每段路径
          path = new Phaser.Curves.Path(pitem[0][0], pitem[0][1]);
          for(let iii = 1; iii < pitem.length; iii++) {
            path.lineTo(pitem[iii][0], pitem[iii][1])
          }
          if (graphics) {
            let color = [0x0000ff, 0xff0000]
            graphics.lineStyle(6, color[ind % 2], 0.5);
            path.draw(graphics, 2);
          }
        })
      }
    })
    // console.log(sCallAgvTasks)

      // let path = new Phaser.Curves.Path(agvX, agvY);
      // for (let iii = 0; iii < pts.length; iii++) {
      //   // x,y
      //   let cpt = pts[iii];
      //   path.lineTo(cpt[0], cpt[1]);
      // }
      // // draw path line
      // if (graphics) {
      //   graphics.lineStyle(6, 0x0000ff, 0.8);
      //   path.draw(graphics, 2);
      // }

      // //对每条路径，计算总长度，让AGV沿路径运动
      // let arr = path.getCurveLengths();
      // let sLen = 0;
      // arr.forEach(function (val, idx, arr) { sLen += val; }, 0);

      // let agv = closest as unknown as Agv;
      // agv.setPath(path);
      // path.getCurveLengths();
      // agv.startFollow({
      //   positionOnPath: true,
      //   duration: sLen / agv.getSpeed(),
      //   yoyo: false,
      //   // repeat: 1,
      //   rotateToPath: true,
      //   // verticalAdjust: true
      // });
    // }, 0);
  }
}
