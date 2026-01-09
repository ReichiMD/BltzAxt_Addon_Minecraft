import { world, system, ItemStack } from "@minecraft/server";

world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;

    // Check if player has the 'test:received_god_sword' dynamic property, which means they've received the starter item.
    // If not, give it to them and set the property.
    if (!player.getDynamicProperty("test:received_god_sword")) {
        const godSword = new ItemStack("test:god_sword", 1);
        player.getComponent("inventory").container.addItem(godSword);
        player.setDynamicProperty("test:received_god_sword", true);
        player.sendMessage("Du hast das One-Hit-Schwert erhalten!");
    }
});
