# WalkingInBulletWorld

A character walking around on uneven terrain in Bullet World

I thought out the way of rotating camera while avoiding walls and other obstacles to follow a character, of making the character go up and down the stairs, and of preventing the character from going through walls when moving fast. And I enjoyed procedurally making all of the houses and bridges. 

The doors automatically open and close. To go in and out at the doors, stop in front of them to wait a little. Pressing [up arrow] key makes the character go up and down stairs. 

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
