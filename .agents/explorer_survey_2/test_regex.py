import re

pattern = re.compile(r'((?P<q>["\']?)(?i:lightCastShadows)(?P=q)\s*:\s*)(?:(?P<vq>["\'])(?:true|True|1)(?P=vq)|(?:true|True|1)\b)')

samples = [
    '"lightCastShadows": true,',
    "'lightCastShadows': true,",
    "lightCastShadows: true,",
    '"lightCastShadows":true,',
    "  lightCastShadows :   true, // comment",
    '"lightCastShadows": false,',
    "lightCastShadows: false,",
    "someOtherField: true,",
    '"lightCastShadows": "true",',
    '"lightCastShadows": 1,',
    '"LightCastShadows": true,'
]

for s in samples:
    subbed, count = pattern.subn(r'\g<1>false', s)
    print(f"{s:40} -> {subbed:40} (replaced: {count})")
