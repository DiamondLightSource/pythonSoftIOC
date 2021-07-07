from p4p.client.cothread import Context

ctx = Context("pva")
print(ctx.get("MY-DEVICE-PREFIX:AI"))
print(ctx.get("MY-DEVICE-PREFIX:AO"))
ctx.put("MY-DEVICE-PREFIX:AO", "999")
print(ctx.get("MY-DEVICE-PREFIX:AO"))
