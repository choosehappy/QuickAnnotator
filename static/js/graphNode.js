class GraphNode {
    // constructor
    constructor(x, y){
        this.x = x;
        this.y = y;
        this.global_cost = 0;
        this.e = false;
        this.inL = false;
        this.prev = null;
        this.next = null;
    }
}