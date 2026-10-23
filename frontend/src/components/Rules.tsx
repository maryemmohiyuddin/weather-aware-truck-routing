export function Rules() {
  return (
    <details className="rules">
      <summary>How risk is scored</summary>
      <p>
        Each checkpoint takes the worst of wind, rain, and snow. Clear weather is Low. A value on a
        shared boundary takes the worse class. Wind bands run up to, but not including, the next
        threshold, so 34.9 mph is moderate and 35 mph is high. Rain at 1.00 in/hr and snow at 3.0
        in/hr are still severe. No-travel starts just above those.
      </p>
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Low</th>
            <th>Mod</th>
            <th>High</th>
            <th>Severe</th>
            <th>No travel</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Wind mph</th>
            <td>&lt;25</td>
            <td>25–34</td>
            <td>35–44</td>
            <td>45–54</td>
            <td>≥55</td>
          </tr>
          <tr>
            <th>Rain in/hr</th>
            <td>&lt;0.10</td>
            <td>0.10–0.25</td>
            <td>0.25–0.50</td>
            <td>0.50–1.00</td>
            <td>&gt;1.00</td>
          </tr>
          <tr>
            <th>Snow in/hr</th>
            <td>&lt;0.5</td>
            <td>0.5–1.0</td>
            <td>1.0–2.0</td>
            <td>2.0–3.0</td>
            <td>&gt;3.0</td>
          </tr>
        </tbody>
      </table>
      <p>
        Load applies to wind only. 55 mph or more is no-travel for any load. 45–54 mph with a load
        over 30,000 lb is no-travel. 35–44 mph with a load over 40,000 lb is severe. Exactly 30,000
        lb or 40,000 lb does not trigger the rule.
      </p>
      <p>
        Each mile of the route uses the nearest checkpoint. Average risk is that distance-weighted
        score: low 1, moderate 2, high 3, severe 4, no-travel 5.
      </p>
    </details>
  );
}
