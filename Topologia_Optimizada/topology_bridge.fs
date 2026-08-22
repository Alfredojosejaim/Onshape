FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

annotation { "Feature Type Name" : "Topology Bridge" }
export const topologyBridge = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Preserve geometry", "Filter" : EntityType.BODY || EntityType.FACE || EntityType.EDGE || EntityType.VERTEX, "MaxNumberOfPicks" : 50, "Item Name" : "entity" }
        definition.preserve is Query;

        annotation { "Name" : "Obstacle geometry", "Filter" : EntityType.BODY || EntityType.FACE || EntityType.EDGE || EntityType.VERTEX, "MaxNumberOfPicks" : 50, "Item Name" : "entity" }
        definition.obstacle is Query;

        annotation { "Name" : "Initial shape (optional)", "Filter" : EntityType.BODY || EntityType.FACE || EntityType.EDGE || EntityType.VERTEX, "MaxNumberOfPicks" : 50, "Item Name" : "entity" }
        definition.initialShape is Query;

        annotation { "Name" : "Constraint geometry", "Filter" : EntityType.FACE || EntityType.EDGE || EntityType.VERTEX, "MaxNumberOfPicks" : 50, "Item Name" : "entity" }
        definition.constraint is Query;

        annotation { "Name" : "Load geometry", "Filter" : EntityType.FACE || EntityType.EDGE || EntityType.VERTEX, "MaxNumberOfPicks" : 50, "Item Name" : "entity" }
        definition.load is Query;
    }
    {
        var roles = [
            { "name" : "preserve", "entities" : definition.preserve },
            { "name" : "obstacle", "entities" : definition.obstacle },
            { "name" : "initialShape", "entities" : definition.initialShape },
            { "name" : "constraint", "entities" : definition.constraint },
            { "name" : "load", "entities" : definition.load }
        ];

        for (var role in roles)
        {
            if (size(evaluateQuery(context, role.entities)) > 0)
            {
                setAttribute(context, {
                    "entities" : role.entities,
                    "name" : "topologyBridgeSelection",
                    "value" : {
                        "schemaVersion" : "1.0",
                        "operation" : "topology-study-definition",
                        "role" : role.name,
                        "parameters" : {},
                        "geometry" : {}
                    }
                });
            }
        }
    });
