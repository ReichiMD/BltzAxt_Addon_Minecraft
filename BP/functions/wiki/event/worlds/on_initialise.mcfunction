## Initialisation
### Add objective
scoreboard objectives add wiki:world dummy
### Register to objective
scoreboard players add .Initialised wiki:world 0

## Your Commands Here (Example)
execute if score .Initialised wiki:world matches 0 run function test:give_god_sword

## Mark as Initialised
scoreboard players set .Initialised wiki:world 1
