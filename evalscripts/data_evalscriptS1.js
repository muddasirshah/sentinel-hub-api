function setup() {
  return {
    input: ["VV", "VH"],
    output: [
        {id: "VV", bands: 1, sampleType: SampleType.FLOAT32},
        {id: "VH", bands: 1, sampleType: SampleType.FLOAT32},
        {id: "WH", bands: 1, sampleType: SampleType.FLOAT32}
    ],
    mosaicking: Mosaicking.ORBIT
  }
}

function preProcessScenes (collections) {
  collections.scenes.orbits.sort(function (s1, s2) {
          var date1 = new Date(s1.dateFrom);
          var date2 = new Date(s2.dateFrom);
          return date1 - date2}) // sort the scenes by dateFrom in ascending order

  firstOrbitDate = new Date(collections.scenes.orbits[0].dateFrom)
  var previousOrbitMonth = firstOrbitDate.getMonth() - 1
  collections.scenes.orbits = collections.scenes.orbits.filter(function (orbit) {
      var currentOrbitDate = new Date(orbit.dateFrom)
      if (currentOrbitDate.getMonth() != previousOrbitMonth){
          previousOrbitMonth = currentOrbitDate.getMonth();
          return true;
      } else return false;
  })
  return collections
}

function updateOutput(outputs, collection) {
  Object.values(outputs).forEach((output) => {
      output.bands = collection.scenes.length;
  });
}

function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
  var dds = [];
  for (i=0; i<scenes.length; i++){
    dds.push(scenes[i].date)
  }
  outputMetadata.userData = { "acquisition_dates":  JSON.stringify(dds) }
}

function toDb(linear) {
  return 10 * Math.log(linear) / Math.LN10
}

function evaluatePixel(samples) {
  var n_observations = samples.length
  
  let array_vv = new Array(n_observations).fill(0)
  let array_vh = new Array(n_observations).fill(0)
  let array_wh = new Array(n_observations).fill(0)
  
  samples.forEach((sample, index) => {
      array_vv[index] = toDb(sample.VV)
      array_vh[index] = toDb(sample.VH)
      array_wh[index] = array_vv[index] / array_vh[index] / 10
  });
  
  return {
      VV: array_vv,
      VH: array_vh,
      WH: array_wh
  }
}
