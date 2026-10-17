(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SifarCharts=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function finite(value){return typeof value==='number'&&Number.isFinite(value)&&value>=0;}
  function quantile(values,p){const sorted=values.filter(finite).sort((a,b)=>a-b);if(!sorted.length)return null;const index=(sorted.length-1)*p,lower=Math.floor(index);return sorted[lower]+(sorted[Math.ceil(index)]-sorted[lower])*(index-lower);}
  function distribution(rows,count=6){
    const points=rows.filter(r=>r.status!=='pending'&&finite(r.elapsed_seconds));
    const max=Math.max(1,...points.map(r=>r.elapsed_seconds));
    const bins=Array.from({length:count},(_,i)=>({lower:i*max/count,upper:(i+1)*max/count,ids:[]}));
    points.forEach(r=>bins[Math.min(count-1,Math.floor(r.elapsed_seconds/max*count))].ids.push(String(r.id)));
    return {bins,count:points.length,median:quantile(points.map(r=>r.elapsed_seconds),.5),p90:quantile(points.map(r=>r.elapsed_seconds),.9),max:points.length?Math.max(...points.map(r=>r.elapsed_seconds)):null};
  }
  function measured(row,metric){
    const u=row.usage;
    if(metric==='time')return row.status!=='pending'&&finite(row.elapsed_seconds)?row.elapsed_seconds:null;
    if(metric==='cost')return u?.cost_complete&&finite(u.actual_cost_usd)?u.actual_cost_usd:null;
    if(metric==='tokens')return u?.tokens_complete&&finite(u.total_tokens)?u.total_tokens:null;
    return null;
  }
  function scatter(rows,metric='cost'){
    const completed=rows.filter(r=>r.status!=='pending');
    const points=completed.map(row=>({id:String(row.id),x:measured(row,'time'),y:measured(row,metric),outcome:row.outcome,repairs:row.repairs||0})).filter(p=>p.x!==null&&p.y!==null);
    return {points,excluded:completed.length-points.length};
  }
  function historyValue(run,metric){
    if(!run.finished)return null;
    if(metric==='match')return run.compared&&run.api_errors<run.completed?100*run.matched/run.compared:null;
    if(metric==='time')return finite(run.elapsed_seconds)?run.elapsed_seconds:null;
    if(metric==='cost')return run.usage?.cost_complete&&finite(run.usage.actual_cost_usd)?run.usage.actual_cost_usd:null;
    return null;
  }
  function segments(points,x,y){let open=false,path='';for(const point of points){if(point.value===null){open=false;continue;}path+=(open?' L ':' M ')+x(point).toFixed(2)+' '+y(point).toFixed(2);open=true;}return path.trim();}
  return {finite,quantile,distribution,measured,scatter,historyValue,segments};
});
