import Phaser from 'phaser'
import TextureKeys from '~/consts/TextureKeys'
import { SceneBusKeys } from '~/consts/SceneKeys'

export default class Tasks extends Phaser.Scene {
    public static WIDTH = 500
    public static HEIGHT = 650
    // private panel!: any
    private parent!: any

    constructor(handle, parent) {
        super(handle);
        this.parent = parent;
    }

    preload() {

    }
    create() {
        this.cameras.main.setViewport(this.parent.x, this.parent.y, Tasks.WIDTH, Tasks.HEIGHT)
        var bg = this.add.image(0, 0, TextureKeys.ZxkWindow).setOrigin(0).setAlpha(0.8).setScale(0.95)
        this.registry.events.on(SceneBusKeys.BusDataChange, this.updateData, this)


        const button = this.add.text(190, 400, '开始规划')
            .setOrigin(0.5)
            .setPadding(10)
            .setStyle({ backgroundColor: '#111' })
            .setInteractive({ useHandCursor: true })
            .on('pointerover', () => button.setStyle({ fill: '#f39c12' }))
            .on('pointerout', () => button.setStyle({ fill: '#FFF' }))

        button.on('clicked', this.clickHandler, this);

        this.input.on('gameobjectup', function (pointer, gameObject) {
            gameObject.emit('clicked', gameObject);
        }, this);

    }

    clickHandler(box) {
        let ret = ''
        let list = box.displayList.list
        let ind = 0
        list.forEach(element => {
            let dt = element.getData('tags')
            if (dt && dt === 'tasks') {
                // [{"s": [480, 228], "e": [87, 253]}, {"s": [490, 271], "e": [160, 300]}]
                ind++
                let prefix = ''
                let suffix = ''
                if (ind % 2 === 0) {
                    prefix = '"e"'
                    suffix = '},'
                } else {
                    prefix = '{"s"'
                    suffix = ','
                }
                let stmp = `${prefix}: [${element.text}]${suffix}`
                // console.log(stmp)
                ret = ret + stmp
            }
        });
        ret = '[' + ret.substring(0, ret.length - 1) + ']'
        // console.log(ret)
        this.registry.set(SceneBusKeys.TopicMAPFCall, ret) //发送任务列表，交Mapf Scene去调用后端REST
    }
    public tasklog = true
    public yind = 0
    updateData(parent, key, data) {
        // console.log(key, data)
        switch (key) {
            case SceneBusKeys.TopicTaskSet:
                // Add new line green item as start point, red one as end point
                let ypos = 0
                let xpos = 0
                this.yind += 1
                if (this.yind % 2) {
                    xpos = 30
                    ypos = 50 + this.yind * 10
                } else {
                    xpos = 160
                    ypos = 50 + (this.yind - 1) * 10
                }
                this.tasklog = !this.tasklog
                let color = '#00ff00'
                if (this.tasklog)
                    color = '#ff0000'
                else
                    color = '#00ff00'
                const sprite = this.add.text(xpos, ypos, `${Math.round(data.x)}, ${Math.round(data.y)}`, { color: color })
                sprite.setData('tags', 'tasks') //用于特殊标记，便于后面作为判断条件使用
                sprite.setInteractive()
                sprite.once('pointerdown', () => {
                    sprite.removeFromDisplayList()
                })
            default:
                break
        }
    }

    update(time, delta) {

    }

    refresh() {
        this.cameras.main.setPosition(this.parent.x, this.parent.y);
        this.scene.bringToTop();
    }

}


class Button {
    public ctx: any
    constructor(x, y, label, scene, callback) {
        this.ctx = scene
        const button = scene.add.text(x, y, label)
            .setOrigin(0.5)
            .setPadding(10)
            .setStyle({ backgroundColor: '#111' })
            .setInteractive({ useHandCursor: true })
            .on('pointerdown', () => callback())
            .on('pointerover', () => button.setStyle({ fill: '#f39c12' }))
            .on('pointerout', () => button.setStyle({ fill: '#FFF' }));
    }
}