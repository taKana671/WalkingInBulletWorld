# WalkingInBulletWorld

A character walking around on uneven terrain in Bullet World

I thought out the way of rotating camera while avoiding walls and other obstacles to follow a character, and of making the character go up and down the stairs. And I enjoyed procedurally making all of the houses and bridges. The doors automatically open and close. To go in and out at the doors, stop in front of them to wait a little. Pressing [up arrow] key makes the character go up and down stairs. 

In the end, I gave up using BulletCharacterControllerNode to make my own character_controller class. I thought first that BulletCharacterControllerNode was very good because it was kinematic body but gravitated to fall. It was difficult to controll all of the movement of a character in BulletWorld by not using the effect of gravity. I'm satisfied now with this character_controller class. But there are still some problems, for example, the character falls from the seam connecting floor blocks when it happens to be on the seam. I want to improve this class step by step.

![DEMO_new](https://user-images.githubusercontent.com/48859041/233696155-3bfe126e-ed1f-47d3-9937-a8623c39cca1.png)

New buildings, which are a maze house, an adventure bridge and an elevator tower, have been added. Carefully cross the adventure bridge made by using Bullet Softbody Rope and Bullet Softbody Patch. Ride on the elevator to go up the roof top, you can see fireworks.

![demo3](https://github.com/taKana671/WalkingInBulletWorld/assets/48859041/73e5e215-76e0-4cd4-93d6-ada5cf5b7eff)

# Requirements
* Panda3D 1.10.13
* pandas 1.5.2
* numpy 1.23.5

# Environment
* Python 3.11
* Windows11

# Usage
* Execute a command below on your command line.
```
>>>python walking.py
```

# Controls:
* Press [Esc] to quit.
* Press [up arrow] key to go foward.
* Press [left arrow] key to turn left.
* Press [right arrow] key to turn right.
* Press [down arrow] key to go back.
* Press [ I ] key to toggle instructions ON and OFF.
* Press [ D ] key to toggle debug ON and OFF.
* Press [ F ] key to toggle ray cast lines ON and OFF.
