class KMeans {
    constructor(data, k = 3, iterations = 100) {
        this.data = data; // [[lat, lng], ...]
        this.k = k;
        this.iterations = iterations;
        this.centroids = [];
    }

    distance(point1, point2) {
        return Math.sqrt(Math.pow(point2[0] - point1[0], 2) + Math.pow(point2[1] - point1[1], 2));
    }

    assignCluster(dataPoint, centroids) {
        let minDist = Infinity;
        let cluster = 0;
        for (let i = 0; i < centroids.length; i++) {
            const dist = this.distance(dataPoint, centroids[i]);
            if (dist < minDist) {
                minDist = dist;
                cluster = i;
            }
        }
        return cluster;
    }

    updateCentroids(clusters) {
        const newCentroids = [];
        for (let i = 0; i < this.k; i++) {
            const points = clusters[i];
            if (points.length === 0) {
                newCentroids.push(this.centroids[i]);
                continue;
            }
            const sum = points.reduce((acc, point) => [acc[0] + point[0], acc[1] + point[1]], [0, 0]);
            newCentroids.push([sum[0] / points.length, sum[1] / points.length]);
        }
        return newCentroids;
    }

    cluster() {
        // Initialize centroids randomly
        this.centroids = this.data.slice(0, this.k);
        
        for (let i = 0; i < this.iterations; i++) {
            const clusters = Array.from({ length: this.k }, () => []);
            
            // Assign points to clusters
            for (let point of this.data) {
                const clusterId = this.assignCluster(point, this.centroids);
                clusters[clusterId].push(point);
            }
            
            // Update centroids
            const newCentroids = this.updateCentroids(clusters);
            
            // Check convergence
            let converged = true;
            for (let j = 0; j < this.k; j++) {
                if (this.distance(this.centroids[j], newCentroids[j]) > 0.001) {
                    converged = false;
                    break;
                }
            }
            this.centroids = newCentroids;
            if (converged) break;
        }
        
        return { centroids: this.centroids, clusters: this.clusters };
    }
}

window.KMeans = KMeans;
