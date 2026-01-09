import { world, system, Player, Entity, Vector3, EquipmentSlot, ItemStack } from "@minecraft/server";

// --- Blitz-Axt Funktionalität --- 

// Event-Listener für Angriffe auf Entitäten
world.afterEvents.entityHitEntity.subscribe((event) => {
    const attacker = event.attackingEntity; // Der angreifende Entität

    // Prüfen, ob der Angreifer ein Spieler ist
    if (!(attacker instanceof Player)) {
        return;
    }

    // Überprüfen, welches Item der Spieler in der Haupt-Hand hält
    const equippable = attacker.getComponent("minecraft:equippable");
    if (!equippable) {
        return;
    }

    const mainhandSlot = equippable.getEquipmentSlot(EquipmentSlot.Mainhand);
    if (!mainhandSlot.hasItem()) {
        return;
    }

    const heldItem = mainhandSlot.getItem();

    // Wenn der Spieler eine Eisenaxt hält, Blitze spawnen
    if (heldItem.typeId === "minecraft:iron_axe") {
        const playerLocation = attacker.location;
        const viewDirection = attacker.getViewDirection();
        const strikeDistance = 5; // Blitze 5 Blöcke vor dem Spieler spawnen

        const lightningX = playerLocation.x + viewDirection.x * strikeDistance;
        const lightningY = playerLocation.y + viewDirection.y * strikeDistance;
        const lightningZ = playerLocation.z + viewDirection.z * strikeDistance;

        const strikeLocation = { x: lightningX, y: lightningY, z: lightningZ };
        const dimension = attacker.dimension;

        // Blitze spawnen
        system.run(() => {
            dimension.spawnEntity("minecraft:lightning_bolt", strikeLocation);
        });
    }
});

// --- Start-Kit Funktionalität (für Tests) --- 

// Event-Listener, der beim Laden der Welt ausgeführt wird, um sich für playerJoin zu abonnieren
world.afterEvents.worldLoad.subscribe(() => {
    world.afterEvents.playerJoin.subscribe((event) => {
        const player = event.player;
        const inventory = player.getComponent("minecraft:inventory");

        if (inventory) {
            const container = inventory.container;
            if (container) {
                // Gibt dem Spieler eine Eisenaxt
                const ironAxe = new ItemStack("minecraft:iron_axe", 1);
                container.addItem(ironAxe);
                player.sendMessage("Du hast eine Blitzaxt (Eisenaxt) erhalten!");
            }
        }
    });
});
