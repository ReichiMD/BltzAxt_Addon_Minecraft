## Initialisation
### Add objective
scoreboard objectives add test:world dummy
### Register to objective
scoreboard players add .Initialised test:world 0

## Your Commands Here (Example)
execute if score .Initialised test:world matches 0 run give @s test:god_sword

## Mark as Initialised
scoreboard players set .Initialised test:world 1