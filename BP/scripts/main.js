import { world, system, ItemStack } from "@minecraft/server";

world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;
    if (event.initialSpawn) {
        system.run(() => {
            const godSword = new ItemStack("test:god_sword", 1);
            player.getComponent("minecraft:inventory").container.addItem(godSword);
            player.sendMessage("Du hast das One-Hit-Schwert erhalten!");
        });
    }
});
