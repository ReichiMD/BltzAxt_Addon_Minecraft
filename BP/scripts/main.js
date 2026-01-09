import { world, system, ItemStack } from '@minecraft/server';
import './lightning_axe_component.js'; // Import the custom item component registration

const BLITZAXT_IDENTIFIER = "test:blitzaxt";
const HAS_BLITZAXT_KIT_PROPERTY = "test:has_blitzaxt_kit";

// Function to give the Blitzaxt to a player if they don't have it yet
function giveBlitzaxtKit(player) {
    if (!player.getDynamicProperty(HAS_BLITZAXT_KIT_PROPERTY)) {
        const blitzaxt = new ItemStack(BLITZAXT_IDENTIFIER, 1);
        player.getComponent('inventory')?.container?.addItem(blitzaxt);
        player.sendMessage("Du hast eine Blitzaxt erhalten!");
        player.setDynamicProperty(HAS_BLITZAXT_KIT_PROPERTY, true);
    }
}

world.afterEvents.worldLoad.subscribe(() => {
    // Give Blitzaxt to all players already in the world when it loads
    for (const player of world.getPlayers()) {
        giveBlitzaxtKit(player);
    }
});

world.afterEvents.playerSpawn.subscribe((event) => {
    // Give Blitzaxt to newly spawned players or players rejoining
    const player = event.player;
    giveBlitzaxtKit(player);
});
