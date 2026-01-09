import { world, system, Player } from "@minecraft/server";

world.afterEvents.worldLoad.subscribe(() => {
    world.sendMessage("Addon Loaded!");
});

// Give the player the Ruby Sword upon joining (for testing purposes)
world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;
    if (event.initialSpawn && player instanceof Player) {
        system.run(() => {
            player.runCommandAsync("give @s test:ruby_sword 1"); // Corrected command with namespace
            player.sendMessage("You received a Ruby Sword!");
        });
    }
});
