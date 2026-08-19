FeatureScript 2464; // Actualizado a una versión moderna estándar
import(path : "onshape/std/geometry.fs") as std; // Importación recomendada para manejar geometría y atributos

annotation { "Feature Type Name" : "Master Topology Input" }
export const masterTopologyInput = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Anclajes", "Filter" : GeometryType.FACE, "MaxNumberOfPicks" : 10, "Item Name" : "anchor" }
        definition.anchors is Query;

        annotation { "Name" : "Carga", "Filter" : GeometryType.FACE, "MaxNumberOfPicks" : 1, "Item Name" : "face" }
        definition.loadFace is Query;

        // En FeatureScript se usa 'is real' en lugar de 'is number'
        annotation { "Name" : "Dirección X" }
        definition.directionX is real;

        annotation { "Name" : "Dirección Y" }
        definition.directionY is real;

        annotation { "Name" : "Dirección Z" }
        definition.directionZ is real;

        annotation { "Name" : "Magnitud (N)" }
        definition.magnitude is real;

        annotation { "Name" : "Fracción de volumen" }
        definition.volumeFraction is real;

        annotation { "Name" : "Número máximo de iteraciones" }
        definition.maxIterations is real;
    }
    {
        // Validaciones
        if (definition.volumeFraction < 0 || definition.volumeFraction > 1)
        {
            throw error("La fracción de volumen debe estar entre 0 y 1");
        }
        if (definition.maxIterations <= 0)
        {
            throw error("El número de iteraciones debe ser mayor a 0");
        }

        var directionX = definition.directionX;
        var directionY = definition.directionY;
        var directionZ = definition.directionZ;

        // Se usa sqrt del paquete std
        var magnitude = std::sqrt(directionX * directionX + directionY * directionY + directionZ * directionZ);

        if (magnitude == 0)
        {
            throw error("La dirección no puede ser un vector cero");
        }

        var loadInfo = {
            "directionX" : directionX / magnitude,
            "directionY" : directionY / magnitude,
            "directionZ" : directionZ / magnitude,
            "magnitude" : definition.magnitude,
            "unit" : "newton"
        };

        var optimizationParams = {
            "volumeFraction" : definition.volumeFraction,
            "maxIterations" : definition.maxIterations
        };

        var topologyData = {
            "schemaVersion" : "1.0",
            "loads" : [loadInfo],
            "optimization" : optimizationParams,
            "timestamp" : "2026-01-01T00:00:00Z"
        };

        // Corrección de almacenamiento: Guardamos los datos en los atributos de las caras seleccionadas
        // Esto permite que un software externo o un exportador lea los metadatos de la carga
        std::setAttribute(context, {
            "entities" : definition.loadFace,
            "name" : "topologyData",
            "value" : topologyData
        });
    });
