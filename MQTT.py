"""Publish HTTP data from particle over MQTT."""

import json
from paho.mqtt.publish import single
from sseclient import SSEClient

# Came from Particle console
addr = "https://api.particle.io/v1/devices/events?access_token=222dbfc46f58a5a4cbfc8ec454360c44aa3947ed"

messages = SSEClient(addr)
# Iterates through ever object in the stream and waits for new objects
for msg in messages:
    if len(msg.data) > 0:
        jMsg = json.loads(msg.data)

        # Data is JSON with some overhead removed, which we need to add back
        raw_data = jMsg['data']
        raw_data = raw_data.replace(':', '":')
        raw_data = raw_data.replace(',', ',"')
        raw_data = '{"' + raw_data + '}'
        print raw_data
        data = json.loads(raw_data)
        for key in data:
            print "Key: %s -- Data: %d" % (key, data[key])
            # Publish to MQTT
            single(topic='particle/' + key, payload=data[key],
                   hostname='test.mosquitto.org')
