# Walkthrough script

About six or seven minutes if you click while you talk. Read it in your own pace. The clicks are in brackets.

---

This is Weather-Aware Truck Routing. A driver gives me a start, an end, a departure time, and how heavy the truck is. I pull three real driving routes, check the forecast at the time the truck would actually be at each point, and recommend the one that is safest without ignoring how long it takes.

[Point at the form.] Origin and destination search as you type. That goes through Photon, with Nominatim as a backup, and it waits a third of a second so we are not hammering the geocoder. Departure is the local time you pick. Load is in pounds.

[Click Chicago to New York.] I'll use the Chicago to New York example so we don't wait on typing. The load on this one is 42,000 pounds, which matters in a minute. The button says it is fetching routes and the 48-hour forecast. That is one request. The slider later does not call the server again.

[When the cards land, point at the three of them, then the map.] Three routes. The public OSRM server usually hands back two alternatives, so if we are short I route through a point offset to the side of the fastest road and keep it only if it actually stays away from the routes we already have. The note under the cards says when that happened. Each card shows distance, time, no-travel miles, severe miles, high miles, and the average risk. The bar is the mix of those classes along the road.

[Read the recommendation sentence out loud.] The order is fixed. Fewest no-travel miles, then fewest severe miles, then fewest high miles, then the lowest average risk, then the shortest time. No-travel is worse than severe, so it is checked first. A route with any no-travel miles loses to a route that has none, even if the clean route has a lot of severe weather. If the forecast is calm, like it may be today, those weather totals tie at zero and the shortest trip wins. That is the rule, not a special case.

[Click a checkpoint.] These dots are every 25 miles, including the end of the route even if the length is not a round number. The popup is the ETA at that point, wind in miles per hour, rain and snow in inches per hour, and the checkpoint risk, which is the worst of the three. The ETA is not the departure time copied down the road. It comes from the driving time of the steps up to that mile.

[Open How risk is scored.] Wind under 25 is low, then moderate up to but not including 35, high up to 45, severe up to 55, and 55 or more is no-travel. So 34.9 is still moderate and 35 is high. Rain and snow share their boundaries, and the worse class wins. One inch of rain per hour is still severe. No-travel rain starts just above that. Same idea for snow at 3 inches.

Load only touches wind, and only to make it worse. Anything 55 or over is no-travel no matter the load. Between 45 and 55, a load over 30,000 pounds becomes no-travel. Between 35 and 45, a load over 40,000 becomes severe. Exactly 30,000 or exactly 40,000 does not count, because the rule says greater than. This Chicago trip is 42,000, so if a checkpoint had wind in the 35 to 44 band, the popup would say the load raised it to severe.

[Click 10 miles, wait for the refresh, then 50.] The sample interval is 10, 25, or 50. Changing it rebuilds the checkpoints, because the miles of risk depend on where we sampled. The dots get denser at 10 and sparser at 50. Each mile of the route is scored by the nearest checkpoint, so one bad sample counts about one interval, and the miles still add up to the length of the route.

[Turn the corridor forecast on if it is off. Drag the slider, then hit Play for a few seconds.] This band is the weather along the trip, not a second request per hour. We fetched the whole 0 to 48 hour grid with the routes, and the slider only redraws it. Play just walks the hours. The color is a continuous severity from wind, rain, and snow, with the same load rules as a floor, so it can move inside a band instead of jumping between five flat colors. Unchecking it hides the heat and leaves the routes.

[Click another route card.] Selecting a card brings that route forward. The recommendation does not change. You are just looking at it.

Under the hood the risky math is not in the React code. Django asks OSRM and Open-Meteo, and the classification, the sampling, and the ranking are plain functions with unit tests. The tests pin the boundaries, including 55 miles an hour, one inch of rain, three inches of snow, and the 30,000 and 40,000 pound lines. Snow is converted from centimeters to inches by dividing by 2.54. Open-Meteo reports snowfall in centimeters, not millimeters, and dividing by 25.4 would make a storm look ten times lighter.

What this does not do: it is a car routing profile, not a truck speed limit or an hours-of-service clock. The public routing and weather servers can rate-limit you. And on a quiet day the winner is simply the fastest route, which you can see in the sentence on the card.
