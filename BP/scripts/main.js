import { world, system, Player, Vector3, EquipmentSlot } from "@minecraft/server";

const AXE_IDENTIFIER = "minecraft:iron_axe";
const LIGHTNING_DISTANCE = 5; // 5 Blöcke in Blickrichtung vor dem Spieler

// --- Start-Kit Logik ---
world.afterEvents.playerSpawn.subscribe((event) => {
    // Überprüfen, ob es sich um die erstmalige Spawnung des Spielers handelt
    if (event.initialSpawn) {
        const player = event.player;
        // Führe den Befehl im nächsten Tick aus, um den "Early-Execution Mode" zu umgehen
        system.run(() => {
            player.runCommandAsync(`give "${player.name}" ${AXE_IDENTIFIER}`);
            player.sendMessage("§aDu hast eine Blitzaxt erhalten!");
        });
    }
});

// --- Blitz-Logik ---
world.afterEvents.entityHitEntity.subscribe((event) => {
    const attackingEntity = event.damagingEntity;

    // Sicherstellen, dass der Angreifer ein Spieler ist
    if (!(attackingEntity instanceof Player)) {
        return;
    }

    // Das Item in der Haupthand des Spielers abrufen
    const equippable = attackingEntity.getComponent("minecraft:equippable");
    if (!equippable) {
        return;
    }
    const heldItem = equippable.getEquipment(EquipmentSlot.Mainhand);

    // Überprüfen, ob das gehaltene Item die Eisenaxt ist
    if (heldItem && heldItem.typeId === AXE_IDENTIFIER) {
        const playerLocation = attackingEntity.location;
        const viewDirection = attackingEntity.getViewDirection();
        const dimension = attackingEntity.dimension;

        // Die Blitzschlagposition berechnen: Spielerposition + (Blickrichtung * Distanz)
        const strikeLocation = {
            x: playerLocation.x + viewDirection.x * LIGHTNING_DISTANCE,
            y: playerLocation.y + viewDirection.y * LIGHTNING_DISTANCE,
            z: playerLocation.z + viewDirection.z * LIGHTNING_DISTANCE,
        };

        // Führe den Befehl im nächsten Tick aus, um die Welt sicher zu modifizieren
        system.run(() => {
            dimension.spawnEntity("minecraft:lightning_bolt", strikeLocation);
            attackingEntity.sendMessage("§bBlitzschlag!");
        });
    }
});
