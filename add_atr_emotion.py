with open('/root/forex-grid/index.html','r') as f:
    content = f.read()
insert = '''  // ATR emotion
  var atr=d.atr||0,emote="--",advice="";
  if(atr<1){emote="DEAD";color="#666";advice="No movement"}
  else if(atr<3){emote="CALM";color="var(--grn)";advice="Full lot, tight grid"}
  else if(atr<6){emote="ACTIVE";color="var(--yel)";advice="Normal conditions"}
  else if(atr<10){emote="VOLATILE";color="var(--orng)";advice="Widen spacing"}
  else if(atr<15){emote="CHAOTIC";color="var(--red)";advice="Halve lot, wide grid"}
  else{emote="CRISIS";color="#a00";advice="Halt recommended"}
  $("atrVal").textContent=atr.toFixed(1)+"p "+emote;
  $("atrVal").style.color=color;
  $("atrSub").textContent=advice;

'''
marker = '  // Grid params badge'
content = content.replace(marker, insert + marker)
with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print('ATR emotion JS inserted')
