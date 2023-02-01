import Phaser from 'phaser'

import Preloader from './scenes/Preloader'
import Game from './scenes/Game'
import GameOver from './scenes/GameOver'
import Controller from './scenes/Controller'
import './styles.css';

const config = {
	type: Phaser.AUTO,
	width: 1920,
	height: 930,
	parent: 'simulator',
	physics: {
		default: 'arcade',
		arcade: {
			gravity: { y: 0 },
			debug: false
		}
	},
	fps: {
		target: 10,
	},
	scene: [Preloader, Controller],
	agvRunning: false,
	runPhase: 0
}
var game = new Phaser.Game(config)
game.config.agvRunning = false;
game.config.runPhase = 0;

export default game
