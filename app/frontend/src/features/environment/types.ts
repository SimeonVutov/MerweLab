export interface EnvironmentOptions {
    trees: boolean;
    elevation: boolean;
    elevationOpacity: number;
}

export interface EnvironmentInfo {
    trees: string;
    elevation: string;
    error: string | null;
}

export interface TreeTile {
    url: string;
    origin: [number, number, number];
    centre: [number, number];
    count: number;
}

export interface EnvironmentManifest {
    version: number;
    trees: {
        tiles: TreeTile[];
        locations: string;
        count: number;
        notes: string;
    };
    elevation: {
        url: string;
        bounds: [number, number, number, number];
        notes: string;
    };
}

export const initialEnvironmentOptions: EnvironmentOptions = {
    trees: false,
    elevation: false,
    elevationOpacity: 0.7,
};

export const initialEnvironmentInfo: EnvironmentInfo = {
    trees: 'Off',
    elevation: 'Off',
    error: null,
};
