
importScripts('https://cdnjs.cloudflare.com/ajax/libs/Turf.js/6.5.0/turf.min.js');

function loadFeatures(data) {
    // load geojson objects from geojson string
    let allFeatures = JSON.parse(data)['features'];
    // reproject and simplify geometries, plus precalc areas
    let features = [];
    for (let i=0; i<allFeatures.length; i++) {
        let feat = allFeatures[i];
        try {
            // NOTE: it matters if simplify is done before or after toWgs84
            // NOTE: toWgs84 is no longer needed, since api data is already wgs84
            feat = turf.simplify(feat, {tolerance:0.001, highQuality:false, mutate:true});
            //feat = turf.buffer(feat, 0);
            //feat = turf.toWgs84(feat); // ol geom web mercator -> turf wgs84
            //feat = turf.simplify(feat, {tolerance:0.01, mutate:true});
            //console.log(turf.bbox(feat))
            feat.properties.area = turf.convertArea(Math.abs(turf.area(feat)),'meters','kilometers');
            features.push(feat);
        } catch(error) {
            console.warn('feature '+i+' could not be loaded: ' + error);
            console.warn(feat.properties);
        };
    };
    return features;
};

function similarity(geom1, geom2) {

    // exit early if no overlap
    /*
    var [xmin1,ymin1,xmax1,ymax1] = turf.bbox(geom1);
    var [xmin2,ymin2,xmax2,ymax2] = turf.bbox(geom2);
    var boxoverlap = (xmin1 <= xmax2 & xmax1 >= xmin2 & ymin1 <= ymax2 & ymax1 >= ymin2)
    if (!boxoverlap) {
        return {'equality':0, 'within':0, 'contains':0}
    };
    */

    // calc intersection
    //alert('calc intersection');
    let isec = turf.intersect(geom1, geom2);
    if (isec == null) {
        // exit early if no intersection
        return {'equality':0, 'within':0, 'contains':0}
    };

    // calc union
    //alert('calc union');
    let union = turf.union(geom1, geom2);

    // calc metrics
    //alert('calc areas');
    let geom1Area = geom1.properties.area;
    let geom2Area = geom2.properties.area;
    let unionArea = turf.convertArea(Math.abs(turf.area(union)), 'meters', 'kilometers');
    let isecArea = turf.convertArea(Math.abs(turf.area(isec)), 'meters', 'kilometers');
    let areas = {'geom1Area':geom1Area, 'geom2Area':geom2Area, 'unionArea':unionArea, 'isecArea':isecArea};
    //alert(JSON.stringify(areas));
    
    let results = {};
    results.equality = isecArea / unionArea;
    results.within = isecArea / geom1Area;
    results.contains = isecArea / geom2Area;

    /*
    if (geom1.properties.pk != geom2.properties.pk) {
        console.log(turf.bbox(geom1))
        console.log(turf.bbox(geom2))
        console.log(geom1)
        console.log(geom2)
        console.log(areas)
        console.log(results)
    };
    */
    return results;
};

function bboxIntersects(bbox1, bbox2) {
    if (bbox1[2] < bbox2[0]) { return false };
    if (bbox1[3] < bbox2[1]) { return false };
    if (bbox1[0] > bbox2[2]) { return false };
    if (bbox1[1] > bbox2[3]) { return false };
    return true;
};

function calcSpatialRelations(feat, features) {
    let matches = [];
    let bbox1 = turf.bbox(feat);
    for (let feat2 of features) {
        let bbox2 = turf.bbox(feat2);
        if (!bboxIntersects(bbox1, bbox2)) {
            continue;
        };
        let simil;
        try {
            simil = similarity(feat, feat2);
        } catch (error) {
            console.warn('error calculating similarity: '+error);
            continue;
        };
        if (simil.equality > 0.0) {
            matches.push([feat2,simil]);
        };
    };
    return matches;
};

function calcAllSpatialRelations(features1, features2) {
    let total = features1.length;
    for (let i=0; i<total; i++) {
        // process
        let feat1 = features1[i];
        matches = calcSpatialRelations(feat1, features2);
        // report back results
        let status = 'processed';
        let msg = [i+1,total,feat1,matches];
        self.postMessage([status,msg]);
    };
};

self.onmessage = function(event) {
    let args = event.data;
    console.log('worker received args');
    // load into feature geojsons
    let data1 = args[0];
    let data2 = args[1];
    let features1 = loadFeatures(data1);
    let features2 = loadFeatures(data2);
    console.log('worker: data loaded')
    // calc relations
    calcAllSpatialRelations(features1, features2);
    console.log('worker: matching done')
    // finish
    let status = 'finished';
    let msg = [];
    self.postMessage([status,msg]);
};
