// Simplified ACO for EV Route Optimization
class ACO {
    constructor(locations, iterations = 100, ants = 20) {
        this.locations = locations; // [{lat, lng}]
        this.numCities = locations.length;
        this.iterations = iterations;
        this.numAnts = ants;
        this.pheromone = this.initializePheromone();
        this.bestRoute = null;
        this.bestDistance = Infinity;
    }

    initializePheromone() {
        const pheromone = [];
        for (let i = 0; i < this.numCities; i++) {
            pheromone[i] = [];
            for (let j = 0; j < this.numCities; j++) {
                pheromone[i][j] = 1.0;
            }
        }
        return pheromone;
    }

    distance(loc1, loc2) {
        const R = 6371; // Earth radius in km
        const dLat = (loc2.lat - loc1.lat) * Math.PI / 180;
        const dLng = (loc2.lng - loc1.lng) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(loc1.lat * Math.PI / 180) * Math.cos(loc2.lat * Math.PI / 180) *
                  Math.sin(dLng/2) * Math.sin(dLng/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    calculateDistance(route) {
        let total = 0;
        for (let i = 0; i < route.length - 1; i++) {
            total += this.distance(this.locations[route[i]], this.locations[route[i+1]]);
        }
        return total;
    }

    getProbability(i, j, visited) {
        let total = 0;
        for (let k = 0; k < this.numCities; k++) {
            if (!visited[k]) {
                total += this.pheromone[i][k];
            }
        }
        return this.pheromone[i][j] / total;
    }

    solve() {
        for (let iter = 0; iter < this.iterations; iter++) {
            const antRoutes = [];
            
            for (let ant = 0; ant < this.numAnts; ant++) {
                const route = this.constructRoute();
                const distance = this.calculateDistance(route);
                antRoutes.push({ route, distance });
                
                if (distance < this.bestDistance) {
                    this.bestDistance = distance;
                    this.bestRoute = route.slice();
                }
            }
            
            this.updatePheromone(antRoutes);
        }
        return this.getOptimizedRoute();
    }

    constructRoute() {
        const route = [0];
        const visited = new Array(this.numCities).fill(false);
        visited[0] = true;
        
        while (route.length < this.numCities) {
            const current = route[route.length - 1];
            const probabilities = [];
            let totalProb = 0;
            
            for (let i = 0; i < this.numCities; i++) {
                if (!visited[i]) {
                    const prob = this.pheromone[current][i];
                    probabilities.push({ index: i, prob });
                    totalProb += prob;
                }
            }
            
            let rand = Math.random() * totalProb;
            for (let prob of probabilities) {
                rand -= prob.prob;
                if (rand <= 0) {
                    route.push(prob.index);
                    visited[prob.index] = true;
                    break;
                }
            }
        }
        return route;
    }

    updatePheromone(antRoutes) {
        // Evaporation
        for (let i = 0; i < this.numCities; i++) {
            for (let j = 0; j < this.numCities; j++) {
                this.pheromone[i][j] *= 0.5;
            }
        }
        
        // Deposition
        for (let antRoute of antRoutes) {
            const route = antRoute.route;
            for (let i = 0; i < route.length - 1; i++) {
                const from = route[i];
                const to = route[i + 1];
                this.pheromone[from][to] += 1.0 / antRoute.distance;
            }
        }
    }

    getOptimizedRoute() {
        return this.bestRoute.map(index => this.locations[index]);
    }
}

// Export for Flask templates
window.ACO = ACO;
