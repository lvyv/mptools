// import { Bullet } from './bullet';
import { IFollowerConstructor } from '../interfaces/follower.interface';

class AssignedTask {
  private id: string
  private paths: Object[]
  private currentPos: number
  constructor() {
    this.id=''
    this.paths = []
    this.currentPos = -1
  }
  public setTaskID(id:string){
    this.id = id
  }
  public getTaskID(): string {
    return this.id
  }
  public appendPath(path: Object) {
    this.paths.push(path)
  }
  public getPaths() {
    return this.paths
  }
  public step(phase) {
    // phase is a global variable, set by controller scene
    // When Mapf scene regulaly update AGV, step is called 
    let res = null
    if(phase == 1) {
      if(this.paths.length > 1) {
        this.currentPos++
        res = this.paths[phase][this.currentPos]
      }
    }else if(phase == 0){
      if(this.paths.length > 0) {
        this.currentPos++
        res = this.paths[phase][this.currentPos]
      }
    }
    return res
  }
}
export class Agv extends Phaser.GameObjects.PathFollower {
  body!: Phaser.Physics.Arcade.Body;

  // variables
  private health!: number;
  // private lastShoot: number;
  private speed: number;

  // children
  // private barrel: Phaser.GameObjects.Image;
  private lifeBar!: Phaser.GameObjects.Graphics;
  private assignedTask !: AssignedTask;
  
  public assignTaskID(id: string): void {
    this.assignedTask.setTaskID(id)
  }
  public checkTaskID(id: string) {
    return id === this.assignedTask.getTaskID()
  }
  public appendTaskPath(path: any): void {
    this.assignedTask.appendPath(path)
  }
  public getAgvTaskID() {
    return this.assignedTask.getTaskID()
  }
  public getAgvTaskPaths() {
    return this.assignedTask.getPaths()
  }

  constructor(aParams: IFollowerConstructor) {
    super(aParams.scene, aParams.path, aParams.x, aParams.y, aParams.texture, aParams.frame);
    if (typeof aParams.speed !== 'undefined') this.speed = aParams.speed;
    else this.speed = 5;
    this.assignedTask = new AssignedTask()
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
    // image
    this.setDepth(10);
    this.lifeBar = this.scene.add.graphics();
    this.redrawLifebar();
    // physics
    this.scene.physics.world.enable(this);
  }

  update(scene): void {
    let runPhase = scene.game.config.runPhase
    let newpos = this.assignedTask.step(runPhase)
    if(newpos) {
      this.x = newpos[0]
      this.y = newpos[1]
    }
    if (this.active) {
      this.lifeBar.x = this.x;
      this.lifeBar.y = this.y;
    } else {
      this.destroy();
      this.lifeBar.destroy();
    }
  }

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
