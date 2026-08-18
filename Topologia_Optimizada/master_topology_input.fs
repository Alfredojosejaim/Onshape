FeatureScript ✨;

import(path : "onshape/std/geometry.fs", version : "2600.0");

annotation { "Feature Type Name" : "Master Topology Input" }
export const masterTopologyInput = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation {
            "Name" : "Anclajes",
            "Filter" : GeometryType.FACE,
            "MaxNumberOfPicks" : 10
        }
        definition.anchors is array of Query;

        annotation {
            "Name" : "Carga",
            "Filter" : GeometryType.FACE,
            "MaxNumberOfPicks" : 1
        }
        definition.loadFace is Query;

        annotation {
            "Name" : "Dirección X",
            "Default" : 0
        }
        definition.directionX is number;

        annotation {
            "Name" : "Dirección Y",
            "Default" : 0
        }
        definition.directionY is number;

        annotation {
            "Name" : "Dirección Z",
            "Default" : -1
        }
        definition.directionZ is number;

        annotation {
            "Name" : "Magnitud",
            "Default" : 100 * newton
        }
        definition.magnitude is ValueWithUnits;

        annotation {
            "Name" : "Fracción de volumen",
            "Default" : 0.30
        }
        definition.volumeFraction is number;

        annotation {
            "Name" : "Número máximo de iteraciones",
            "Default" : 100
        }
        definition.maxIterations is number;
    }
    {
        // Validaciones
        if (definition.volumeFraction < 0 || definition.volumeFraction > 1) {
            throw "La fracción de volumen debe estar entre 0 y 1";
        }
        if (definition.maxIterations <= 0) {
            throw "El número de iteraciones debe ser mayor a 0";
        }
        if (definition.anchors.size() == 0) {
            throw "Debe seleccionar al menos un anclaje";
        }

        var loadFaceData = evPlane(context, {
            "face" : definition.loadFace
        });

        var loadDirection = {
            "x" : definition.directionX,
            "y" : definition.directionY,
            "z" : definition.directionZ
        };

        var normalizedDirection = normalize(loadDirection);

        var loadInfo = {
            "direction" : normalizedDirection,
            "magnitude" : definition.magnitude,
            "unit" definition.magnitude.unit
        };

        var optimizationParams = {
            "volumeFraction" : definition.volumeFraction,
            "maxIterations" : definition.maxIterations
        };

        // Serializar información de anclajes
        var anchorsData = [];
        for (var anchor in definition.anchors) {
            try {
                var anchorArea = evArea(context, {
                    "entities" : anchor
                });
                anchorsData = append(anchorsData, {
                    "area" : anchorArea,
                    "index" : anchorsData.size()
                });
            } catch {
                // Si falla obtener el área, incluir solo el índice
                anchorsData = append(anchorsData, {
                    "index" : anchorsData.size()
                });
            }
        }

        var result = {
            "schemaVersion" : "1.0",
            "anchors" : anchorsData,
            "loads" : [loadInfo],
            "optimization" : optimizationParams,
            "timestamp" : "2024-01-01T00:00:00Z"
        };

        var resultString = JSON.stringify(result);
        setAttribute(context, id, "topologyData", resultString);
    }
);

function normalize(direction) {
    var length = Math.sqrt(direction.x * direction.x + direction.y * direction.y + direction.z * direction.z);
    if (length == 0) {
        throw "La dirección no puede ser un vector cero";
    }
    return {
        "x" : direction.x / length,
        "y" : direction.y / length,
        "z" : direction.z / length
    };
}
