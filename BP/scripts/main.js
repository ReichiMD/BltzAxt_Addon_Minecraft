import { world, system } from "@minecraft/server";

world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;
    system.run(() => {
        try {
            player.runCommandAsync("give @s test:emerald_axe");
            player.sendMessage("Du hast deine Smaragd Axt erhalten!");
        } catch (error) {
            console.error(`Failed to give emerald axe to ${player.name}: ${error}`);
        }
    });
});