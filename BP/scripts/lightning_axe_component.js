import { system, world, Vector3 } from '@minecraft/server';

/** @type {import("@minecraft/server").ItemCustomComponent} */
const ItemLightningStrikeComponent = {
    onHitEntity(event) {
        const { attackingEntity, hitEntity } = event;

        if (!attackingEntity || !hitEntity) {
            return; // Ensure both entities exist
        }

        const dimension = attackingEntity.dimension; // Get the dimension where the attack happened
        const hitLocation = hitEntity.location; // Get the location of the hit entity

        // Strike lightning at the hit entity's location
        // The strikeLightning method requires a Vector3.
        // entity.location returns a Vector3 already.
        dimension.strikeLightning(hitLocation);
    },
};

system.beforeEvents.startup.subscribe(({ itemComponentRegistry }) => {
    // Register the custom component
    itemComponentRegistry.registerCustomComponent("test:lightning_strike_on_hit", ItemLightningStrikeComponent);
});
