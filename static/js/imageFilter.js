Filters = {};
Filters.grayscale = function(image){
    let d = image.data;
    for (let i=0; i<d.length; i+=4) {
        let r = d[i];
        let g = d[i+1];
        let b = d[i+2];
        // CIE luminance for the RGB
        // The human eye is bad at seeing red and blue, so we de-emphasize them.
        let v = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        d[i] = d[i+1] = d[i+2] = v
    }
    return image;
};

Filters.createImageData = function(w, h){
    let tmp_canvas = document.createElement("canvas");
    let tmp_ctx = tmp_canvas.getContext("2d");
    return tmp_ctx.createImageData(w,h);
};

Filters.convolute = function(image, weights){
    let side = Math.round(Math.sqrt(weights.length));
    let halfSide = Math.floor(side / 2);
    let src = image.data;
    let sw = image.width;
    let sh = image.height;

    // pad output by the convolution matrix
    let w = sw;
    let h = sh;
    let dst = [];

    // go through the destination image pixels
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            let sy = y;
            let sx = x;
            // calculate the weighed sum of the source image pixels that
            // fall under the convolution matrix
            let r = 0, g = 0, b = 0;
            for (let cy = 0; cy < side; cy++) {
                for (let cx = 0; cx < side; cx++) {
                    let scy = sy + cy - halfSide;
                    let scx = sx + cx - halfSide;
                    if (scy >= 0 && scy < sh && scx >= 0 && scx < sw) {
                        let srcOff = (scy * sw + scx) * 4;
                        let wt = weights[cy * side + cx];
                        r += src[srcOff] * wt;
                        g += src[srcOff + 1] * wt;
                        b += src[srcOff + 2] * wt;
                    }
                }
            }
            dst.push(r);
            dst.push(g);
            dst.push(b);
            dst.push(255);
        }
    }
    return dst;
};

Filters.sobelFilter = function(image){
    let vertical = Filters.convolute(image,
        [ -1, 0, 1,
        -1, 0, 2,
        -1, 0, 1 ]);
    let horizontal = Filters.convolute(image,
        [ -1, -1, -1,
        0,  0,  0,
        1,  2,  1 ]);
    let dst = [];
    let gv_gradient = [];
    let gh_gradient = [];
    let maxG = 0;

    for (let i = 0; i < vertical.length; i += 4) {
        let gv = Filters.findMax(vertical[i], vertical[i + 1], vertical[i + 2]);
        let gh = Filters.findMax(horizontal[i], horizontal[i + 1], horizontal[i + 2]);
        let gvh = Math.sqrt(Math.pow(gv, 2) + Math.pow(gh, 2));
        maxG = Math.max(maxG, gvh);
        dst.push(gvh);
        gv_gradient.push(gv);
        gh_gradient.push(gh);
    }

    return {
        gradient: dst,
        maxG: maxG,
        gv_gradient: gv_gradient,
        gh_gradient: gh_gradient
    };
};

Filters.findMax = function(a, b, c){
    let temp_max = 0;
    temp_max = Math.max(temp_max, Math.abs(a));
    temp_max = Math.max(temp_max, Math.abs(b));
    temp_max = Math.max(temp_max, Math.abs(c));
    return temp_max;
};

Filters.laplacianFilter = function(image){
    return Filters.convolute(image,
        [ 0,  1, 0,
          1, -4, 1,
          0,  1, 0 ]);
};

Filters.zeroCrossing = function(image){
    let laplacian = Filters.laplacianFilter(image); // 4 channels, alpha = 255
    let dst; // one channel
    let w = image.width, h = image.height;
    (dst = []).length = w * h;
    dst.fill(0);

    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            let dstOff = y * w + x;
            if (laplacian[dstOff * 4] != 0 && laplacian[dstOff * 4 + 1] != 0 && laplacian[dstOff * 4 + 2] != 0){
                // check if the current point is the closest point to 0 in the laplacian map, and
                // if opposite signs appear
                for (let i = -1; i <= 1; i++){
                    for (let j = -1; j <= 1; j++) {
                        for (let c = 0; c < 3; c++) {
                            let positive = laplacian[dstOff * 4 + c] > 0 ? true : false;
                            if (laplacian[((y + i) * w + (x + j)) * 4 + c]> 0 ? true : false != positive) {
                                if (Math.abs(laplacian[dstOff * 4 + c]) < Math.abs(laplacian[((y + i) * w + (x + j)) * 4 + c])){
                                    dst[dstOff] = 255;
                                }
                                else{
                                    dst[(y + i) * w + (x + j)] = 255;
                                }
                            }
                        }
                    }
                }
            } else{
                dst[dstOff] = 255;
            }
        }
    }
    return dst;
};
