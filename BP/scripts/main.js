import { world, system, ItemStack } from "@minecraft/server";

// Wait until the world is loaded to register events
world.afterEvents.worldLoad.subscribe(() => {
    world.afterEvents.playerSpawn.subscribe((event) => {
        const player = event.player;
        // Give the item only on initial spawn
        if (event.initialSpawn) {
            system.run(() => {
                // Create the Emerald Axe item stack
                const emeraldAxe = new ItemStack("test:emerald_axe", 1);
                // Get the player's inventory and add the item
                player.getComponent("minecraft:inventory").container.addItem(emeraldAxe);
                player.sendMessage("Du hast eine Smaragd Axt erhalten!");
            });
        }
    });
});