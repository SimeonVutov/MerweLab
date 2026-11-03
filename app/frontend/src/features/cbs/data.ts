export interface CbsMetric {
    key: string;
    label: string;
    unit: string;
    group: string;
}

export type CbsValue = string | number | null;
export type CbsRing = number[][];
export type CbsPolygon = CbsRing[];

export interface CbsFeature {
    type: 'Feature';
    id: string;
    properties: Record<string, CbsValue> & { buurtcode: string; buurtnaam: string };
    geometry:
        | { type: 'Polygon'; coordinates: CbsPolygon }
        | { type: 'MultiPolygon'; coordinates: CbsPolygon[] };
}

export interface CbsData {
    version: number;
    neighbourhoods: { type: 'FeatureCollection'; features: CbsFeature[] };
    summary: (Record<string, CbsValue> & { variable: string })[];
    bounds: [number, number, number, number];
    reference_year: number | null;
}

export interface CbsOptions {
    enabled: boolean;
    metric: string;
    selected: string | null;
    opacity: number;
    focusRequest: number;
}

const definitions: [string, string, string, string][] = [
    ['aantalInwoners', 'Population', 'people', 'Population'],
    ['aantalHuishoudens', 'Households', 'households', 'Population'],
    ['percentagePersonen0Tot15Jaar', 'Age 0–14', '%', 'Age'],
    ['percentagePersonen15Tot25Jaar', 'Age 15–24', '%', 'Age'],
    ['percentagePersonen25Tot45Jaar', 'Age 25–44', '%', 'Age'],
    ['percentagePersonen45Tot65Jaar', 'Age 45–64', '%', 'Age'],
    ['percentagePersonen65JaarEnOuder', 'Age 65+', '%', 'Age'],
    ['percentageEenpersoonshuishoudens', 'One-person households', '%', 'Households'],
    ['percentageHuishoudensZonderKinderen', 'Households without children', '%', 'Households'],
    ['percentageHuishoudensMetKinderen', 'Households with children', '%', 'Households'],
    ['personenautosPerHuishouden', 'Cars per household', 'cars/household', 'Housing and cars'],
    ['percentageKoopwoningen', 'Owner-occupied homes', '%', 'Housing and cars'],
    ['percHuurwoningenInBezitWoningcorporaties', 'Housing corporation rentals', '%', 'Housing and cars'],
    ['groteSupermarktGemiddeldeAfstandInKm', 'Large supermarket', 'km', 'Facility distance'],
    ['winkelsOvDagelijkseLevensmGemAfstInKm', 'Other daily shopping', 'km', 'Facility distance'],
    ['huisartsenpraktijkGemiddeldeAfstandInKm', 'GP practice', 'km', 'Facility distance'],
    ['apotheekGemiddeldeAfstandInKm', 'Pharmacy', 'km', 'Facility distance'],
    ['kinderdagverblijfGemiddeldeAfstandInKm', 'Day care', 'km', 'Facility distance'],
    ['basisonderwijsGemiddeldeAfstandInKm', 'Primary school', 'km', 'Facility distance'],
    ['treinstationGemiddeldeAfstandInKm', 'Train station', 'km', 'Facility distance'],
];

export const cbsMetrics: CbsMetric[] = definitions.map(([key, label, unit, group]) => ({
    key,
    label,
    unit,
    group,
}));

export const cbsGroups = Array.from(new Set(cbsMetrics.map((metric) => metric.group)));
export const cbsColours = ['#eff3ff', '#bdd7e7', '#6baed6', '#3182bd', '#08519c'];
export const cbsNoDataColour = '#949a96';
export const initialCbsOptions: CbsOptions = {
    enabled: false,
    metric: 'aantalInwoners',
    selected: null,
    opacity: 0.55,
    focusRequest: 0,
};

let request: Promise<CbsData> | undefined;

function validRing(ring: CbsRing) {
    if (!Array.isArray(ring) || ring.length < 4) {
        return false;
    }

    const validPoints = ring.every((point) => Array.isArray(point)
        && point.length >= 2 && point.every(Number.isFinite)
        && point[0]! >= -180 && point[0]! <= 180
        && point[1]! >= -90 && point[1]! <= 90);
    const first = ring[0];
    const last = ring[ring.length - 1];

    return validPoints && first?.[0] === last?.[0] && first?.[1] === last?.[1];
}

export function validateCbs(data: CbsData) {
    if (data.version !== 1 || data.neighbourhoods?.type !== 'FeatureCollection'
        || !Array.isArray(data.neighbourhoods.features) || !data.neighbourhoods.features.length
        || !Array.isArray(data.summary) || !Array.isArray(data.bounds)
        || data.bounds.length !== 4 || !data.bounds.every(Number.isFinite)) {
        throw new Error('Invalid CBS dataset');
    }

    const [west, south, east, north] = data.bounds;
    if (!(west < east && south < north)) {
        throw new Error('Invalid CBS coverage bounds');
    }

    const codes = new Set<string>();
    for (const feature of data.neighbourhoods.features) {
        if (!feature || feature.type !== 'Feature' || typeof feature.id !== 'string'
            || feature.properties?.buurtcode !== feature.id
            || typeof feature.properties.buurtnaam !== 'string' || codes.has(feature.id)) {
            throw new Error('Invalid or duplicate CBS neighbourhood');
        }

        const geometry = feature.geometry;
        let polygons: CbsPolygon[];
        if (geometry?.type === 'Polygon') {
            polygons = [geometry.coordinates];
        } else if (geometry?.type === 'MultiPolygon') {
            polygons = geometry.coordinates;
        } else {
            throw new Error('CBS neighbourhoods require polygon geometry');
        }

        if (!Array.isArray(polygons) || !polygons.length
            || !polygons.every((polygon) => Array.isArray(polygon)
                && polygon.length > 0 && polygon.every(validRing))) {
            throw new Error('Invalid CBS neighbourhood boundary');
        }

        for (const metric of cbsMetrics) {
            const value = feature.properties[metric.key];
            if (value !== null && (typeof value !== 'number' || !Number.isFinite(value) || value < 0)) {
                throw new Error(`Invalid CBS indicator: ${metric.key}`);
            }
        }

        codes.add(feature.id);
    }

    for (const row of data.summary) {
        if (!row || typeof row.variable !== 'string') {
            throw new Error('Invalid CBS regional comparison');
        }

        for (const [key, value] of Object.entries(row)) {
            if (key !== 'variable' && value !== null
                && (typeof value !== 'number' || !Number.isFinite(value) || value < 0)) {
                throw new Error('Invalid CBS regional comparison value');
            }
        }
    }
}

async function fetchCbs(): Promise<CbsData> {
    const response = await fetch('/web/cbs/data.json');
    if (!response.ok) {
        throw new Error(`CBS data returned HTTP ${response.status}`);
    }

    if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('CBS data is not being served. Restart the frontend server.');
    }

    const data: CbsData = await response.json();
    validateCbs(data);

    return data;
}

export function loadCbs(): Promise<CbsData> {
    if (!request) {
        request = fetchCbs().catch((cause: unknown) => {
            request = undefined;
            throw cause;
        });
    }

    return request;
}

export function cbsRange(data: CbsData, metric: string): [number, number] | null {
    const values = data.neighbourhoods.features
        .map((feature) => feature.properties[metric])
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));

    if (!values.length) {
        return null;
    }

    return [Math.min(...values), Math.max(...values)];
}

export function cbsColour(value: unknown, range: [number, number] | null) {
    if (typeof value !== 'number' || !Number.isFinite(value) || !range) {
        return cbsNoDataColour;
    }

    let fraction = 0.5;
    if (range[1] !== range[0]) {
        fraction = (value - range[0]) / (range[1] - range[0]);
    }

    const index = Math.min(cbsColours.length - 1, Math.max(0, Math.floor(fraction * cbsColours.length)));
    return cbsColours[index]!;
}

function ringContainsPoint(ring: CbsRing, longitude: number, latitude: number) {
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
        const start = ring[previous]!;
        const end = ring[index]!;
        const crossesLatitude = (start[1]! > latitude) !== (end[1]! > latitude);
        if (!crossesLatitude) {
            continue;
        }

        const intersection = (end[0]! - start[0]!) * (latitude - start[1]!)
            / (end[1]! - start[1]!) + start[0]!;
        if (longitude < intersection) {
            inside = !inside;
        }
    }

    return inside;
}

export function cbsFeatureAt(data: CbsData, longitude: number, latitude: number) {
    return data.neighbourhoods.features.find((feature) => {
        let polygons: CbsPolygon[];
        if (feature.geometry.type === 'MultiPolygon') {
            polygons = feature.geometry.coordinates;
        } else {
            polygons = [feature.geometry.coordinates];
        }

        return polygons.some(([outer, ...holes]) => {
            const inOuter = ringContainsPoint(outer!, longitude, latitude);
            const inHole = holes.some((hole) => ringContainsPoint(hole, longitude, latitude));
            return inOuter && !inHole;
        });
    });
}
