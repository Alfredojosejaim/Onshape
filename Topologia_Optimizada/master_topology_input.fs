FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

annotation { "Feature Type Name" : "Master Topology Input" }
export const masterTopologyInput = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Anchors", "Filter" : EntityType.FACE,
            "MaxNumberOfPicks" : 10, "Item Name" : "anchor" }
        definition.anchors is Query;

        annotation { "Name" : "Load Face", "Filter" : EntityType.FACE,
            "MaxNumberOfPicks" : 1, "Item Name" : "face" }
        definition.loadFace is Query;

        annotation { "Name" : "Direction X" }
        isReal(definition.directionX, { (unitless) : [-1e5, 0.0, 1e5] } as RealBoundSpec);
        annotation { "Name" : "Direction Y" }
        isReal(definition.directionY, { (unitless) : [-1e5, 0.0, 1e5] } as RealBoundSpec);
        annotation { "Name" : "Direction Z" }
        isReal(definition.directionZ, { (unitless) : [-1e5, 0.0, 1e5] } as RealBoundSpec);
        annotation { "Name" : "Magnitude (N)" }
        isReal(definition.magnitude, { (unitless) : [0.0, 100.0, 1e5] } as RealBoundSpec);
        annotation { "Name" : "Volume Fraction" }
        isReal(definition.volumeFraction, { (unitless) : [0.0, 0.5, 1.0] } as RealBoundSpec);
        annotation { "Name" : "Max Iterations" }
        isInteger(definition.maxIterations, { (unitless) : [1, 20, 1000] } as IntegerBoundSpec);
    }
    {
        var directionLength = sqrt(definition.directionX * definition.directionX
            + definition.directionY * definition.directionY
            + definition.directionZ * definition.directionZ);
        if (directionLength == 0.0)
            throw "La direccion no puede ser un vector cero";
        if (definition.magnitude < 0.0)
            throw "La magnitud no puede ser negativa";

        // getCurrentDateTime() is evaluated by Onshape when the feature runs.
        // It is intentionally stored as a native attribute value, not a
        // fabricated identifier or a hardcoded string.
        var topologyData = {
            "schemaVersion" : "1.0",
            "anchors" : { "count" : size(evaluateQuery(context, definition.anchors)) },
            "loads" : [{
                "directionX" : definition.directionX / directionLength,
                "directionY" : definition.directionY / directionLength,
                "directionZ" : definition.directionZ / directionLength,
                "magnitude" : definition.magnitude,
                "unit" : "newton"
            }],
            "optimization" : {
                "volumeFraction" : definition.volumeFraction,
                "maxIterations" : definition.maxIterations
            },
            "timestamp" : getCurrentDateTime()
        };

        // Role attributes persist with the selected faces.  The load face
        // carries the shared configuration; anchors carry only their role.
        setAttribute(context, {
            "entities" : definition.anchors,
            "name" : "topologyAnchor",
            "attribute" : { "schemaVersion" : "1.0", "role" : "anchor" }
        });
        setAttribute(context, {
            "entities" : definition.loadFace,
            "name" : "topologyData",
            "attribute" : topologyData
        });
    });
