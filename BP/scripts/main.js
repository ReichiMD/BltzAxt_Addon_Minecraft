import { world, system } from "@minecraft/server";

const itemIdentifier = "test:emerald_axe";

world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;
    system.run(() => {
        player.runCommandAsync(`give "${player.name}" ${itemIdentifier}`);
        player.sendMessage(`You received a ${itemIdentifier}!`);
    });
});
