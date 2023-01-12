import Phaser from 'phaser'

import Preloader from './scenes/Preloader'
import Game from './scenes/Game'
import GameOver from './scenes/GameOver'
import Controller from './scenes/Controller'
import './styles.css';

const config: Phaser.Types.Core.GameConfig = {
	type: Phaser.AUTO,
	width: 1920,
	height: 930,
	parent: 'simulator',
	physics: {
		default: 'arcade',
		arcade: {
			gravity: { y: 0 },
			debug: true
		}
	},
	fps: {
		target: 20,
	},
	scene: [Preloader, Controller] //, Game, GameOver]
	// scene: [Preloader, Game, GameOver]

}

export default new Phaser.Game(config)
