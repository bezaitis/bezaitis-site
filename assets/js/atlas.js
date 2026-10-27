// The travel map. Renders every [data-map] element on the page:
//   full     the trips page atlas: year filter, regional views, linked index
//   compact  the home page map: click a country to see its trips
//   locator  a small map on each trip page with that trip's country in magenta
// Trip data comes from <script id="trip-data">, written by build.py.
(() => {
  const dataEl = document.getElementById("trip-data");
  if (!dataEl || !window.d3 || !window.topojson) return;

  const { trips, names } = JSON.parse(dataEl.textContent);
  const NS = "http://www.w3.org/2000/svg";
  const W = 1000;
  const latest = trips[0];
  const REGIONS = {
    europe: [[-12, 34], [35, 71]],
    asia: [[95, 5], [137, 46]],
  };

  const byCountry = new Map();
  trips.forEach((t) => t.countries.forEach((c) => {
    if (!byCountry.has(c)) byCountry.set(c, []);
    byCountry.get(c).push(t);
  }));

  const atlasCache = {};
  const loadAtlas = (url) =>
    (atlasCache[url] ||= fetch(url)
      .then((r) => r.json())
      .then((w) => topojson.feature(w, w.objects.countries).features.filter((f) => f.id !== "010")));

  const node = (tag, attrs = {}) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  };

  const plural = (n) => `${n} ${n === 1 ? "trip" : "trips"}`;

  document.querySelectorAll("[data-map]").forEach((root) =>
    init(root).catch(() => {
      const fb = root.querySelector(".map-fallback");
      if (fb) fb.textContent = "The map could not load. Every trip is listed on this page.";
    })
  );

  async function init(root) {
    const mode = root.dataset.map;
    const features = await loadAtlas(root.dataset.atlas);
    const H = mode === "locator" ? 667 : 500;
    const focus = trips.find((t) => t.slug === root.dataset.focus);

    let projection;
    if (mode === "locator" && focus) {
      const own = features.filter((f) => focus.countries.includes(f.id));
      const center = focus.pin || d3.geoCentroid({ type: "FeatureCollection", features: own });
      // A city trip zooms in on the city; a country trip frames the country.
      let radius = 11;
      if (!focus.pin && own.length) {
        const [[x0, y0], [x1, y1]] = d3.geoBounds({ type: "FeatureCollection", features: own });
        const diag = (d3.geoDistance([x0, y0], [x1, y1]) * 180) / Math.PI;
        radius = Math.min(45, Math.max(12, diag * 0.9));
      }
      projection = d3.geoAzimuthalEqualArea()
        .rotate([-center[0], -center[1]])
        .clipAngle(90)
        .fitExtent([[0, 0], [W, H]], d3.geoCircle().center(center).radius(radius)());
    } else {
      projection = d3.geoNaturalEarth1().fitExtent([[4, 4], [W - 4, H - 4]], { type: "FeatureCollection", features });
    }
    const path = d3.geoPath(projection);

    const svg = node("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "xMidYMid meet" });
    svg.classList.add("is-world");
    const g = node("g", { class: "map-g" });
    svg.append(g);
    g.append(node("path", { class: "sphere", d: path({ type: "Sphere" }) }));
    if (mode !== "compact") g.append(node("path", { class: "graticule", d: path(d3.geoGraticule10()) }));

    const visitedIds = mode === "locator" ? new Set(focus ? focus.countries : []) : new Set(byCountry.keys());
    const land = features.filter((f) => !visitedIds.has(f.id));
    g.append(node("path", { class: "land", d: path({ type: "FeatureCollection", features: land }) }));

    const countryPaths = new Map();
    features.filter((f) => visitedIds.has(f.id)).forEach((f) => {
      const p = node("path", { class: "visited", d: path(f), "data-id": f.id });
      if (mode === "locator") {
        p.classList.add(focus.pin ? "is-host" : "is-focus");
      } else {
        const list = byCountry.get(f.id);
        if (latest.countries.includes(f.id)) p.classList.add("is-latest");
        p.setAttribute("tabindex", "0");
        p.setAttribute("role", "button");
        p.setAttribute("aria-label", `${names[f.id]}, ${plural(list.length)}`);
        const title = node("title");
        title.textContent = `${names[f.id]}: ${list.map((t) => t.title).join(", ")}`;
        p.append(title);
      }
      g.append(p);
      countryPaths.set(f.id, p);
    });

    const pins = [];
    const pinTrips = mode === "locator" ? (focus && focus.pin ? [focus] : []) : trips.filter((t) => t.pin);
    pinTrips.forEach((t) => {
      const [x, y] = projection(t.pin);
      const pin = node("g", { class: "pin" });
      pin.append(node("circle", { r: mode === "full" ? 4 : mode === "locator" ? 9 : 3.5 }));
      if (mode === "locator") {
        pin.append(node("circle", { r: 26, class: "latest-ring" }));
        const label = node("text", { x: 36, y: 12, class: "city-label" });
        label.textContent = t.title;
        pin.append(label);
      } else if (mode === "full") {
        const label = node("text", { x: 7, y: 4 });
        label.textContent = t.title;
        pin.append(label);
      }
      if (mode === "locator") pin.classList.add("is-focus");
      else if (t === latest) pin.classList.add("is-latest");
      pin.style.transform = `translate(${x}px, ${y}px)`;
      pin.dataset.slug = t.slug;
      pin.dataset.x = x;
      pin.dataset.y = y;
      g.append(pin);
      pins.push(pin);
    });

    // A ring around the latest trip, so a small country still reads at world scale.
    if (mode !== "locator" && !latest.pin) {
      const own = features.filter((f) => latest.countries.includes(f.id));
      const [x, y] = path.centroid({ type: "FeatureCollection", features: own });
      const ring = node("g", { class: "pin" });
      ring.append(node("circle", { r: 13, class: "latest-ring" }));
      const label = node("text", { x: 18, y: 5, class: "latest-label" });
      label.textContent = latest.title;
      ring.append(label);
      ring.style.transform = `translate(${x}px, ${y}px)`;
      ring.dataset.slug = latest.slug;
      ring.dataset.x = x;
      ring.dataset.y = y;
      g.append(ring);
      pins.push(ring);
    }

    root.querySelector(".map-fallback")?.remove();
    root.append(svg);

    if (mode === "locator") {
      root.setAttribute("role", "img");
      svg.setAttribute("aria-hidden", "true");
      return;
    }

    const state = { year: "all" };
    const matches = (t) => state.year === "all" || t.date.startsWith(state.year);
    const pop = makePopover(root);

    countryPaths.forEach((p, id) => {
      const open = (evt) => {
        const box = root.getBoundingClientRect();
        let x, y;
        if (evt.clientX) {
          x = evt.clientX - box.left;
          y = evt.clientY - box.top;
        } else {
          const r = p.getBoundingClientRect();
          x = r.left + r.width / 2 - box.left;
          y = r.top + r.height / 2 - box.top;
        }
        pop.show(id, byCountry.get(id).filter(matches), x, y, p);
      };
      p.addEventListener("click", open);
      p.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open(e);
        }
      });
    });

    if (mode !== "full") return;

    // Trips page: filters, views and the linked index.
    const shell = root.closest("[data-atlas-root]");
    const rows = [...shell.querySelectorAll(".atlas-index a[data-slug]")];
    const yearSections = [...document.querySelectorAll(".year[data-years]")];
    const cards = [...document.querySelectorAll(".year .trip-card[data-year]")];

    const hot = (slugs, on) => {
      const set = new Set(slugs);
      trips.filter((t) => set.has(t.slug)).forEach((t) =>
        t.countries.forEach((c) => countryPaths.get(c)?.classList.toggle("is-hot", on))
      );
      rows.forEach((r) => r.classList.toggle("is-hot", on && set.has(r.dataset.slug)));
    };
    rows.forEach((r) => {
      const on = () => hot([r.dataset.slug], true);
      const off = () => hot([r.dataset.slug], false);
      r.addEventListener("mouseenter", on);
      r.addEventListener("mouseleave", off);
      r.addEventListener("focus", on);
      r.addEventListener("blur", off);
    });
    countryPaths.forEach((p, id) => {
      const slugs = byCountry.get(id).map((t) => t.slug);
      p.addEventListener("mouseenter", () => hot(slugs, true));
      p.addEventListener("mouseleave", () => hot(slugs, false));
    });

    const applyYear = () => {
      const shown = trips.filter(matches);
      countryPaths.forEach((p, id) => p.classList.toggle("is-dim", !byCountry.get(id).some(matches)));
      pins.forEach((pin) => pin.classList.toggle("is-dim", !matches(trips.find((t) => t.slug === pin.dataset.slug))));
      rows.forEach((r) => (r.parentElement.hidden = state.year !== "all" && r.dataset.year !== state.year));
      cards.forEach((c) => (c.hidden = state.year !== "all" && c.dataset.year !== state.year));
      yearSections.forEach((s) => (s.hidden = state.year !== "all" && !s.dataset.years.split(" ").includes(state.year)));
      shell.querySelector('[data-stat="trips"]').textContent = shown.length;
      shell.querySelector('[data-stat="countries"]').textContent = new Set(shown.flatMap((t) => t.countries)).size;
      const years = shown.map((t) => t.date.slice(0, 4));
      const lo = years[years.length - 1];
      const hi = years[0];
      shell.querySelector('[data-stat="span"]').textContent = lo === hi ? lo : `${lo} to ${hi}`;
      pop.hide();
    };

    const setView = (view) => {
      let k = 1, tx = 0, ty = 0;
      if (REGIONS[view]) {
        const [[lon0, lat0], [lon1, lat1]] = REGIONS[view];
        const pts = [];
        for (let i = 0; i <= 8; i++) {
          const lon = lon0 + ((lon1 - lon0) * i) / 8;
          const lat = lat0 + ((lat1 - lat0) * i) / 8;
          pts.push([lon, lat0], [lon, lat1], [lon0, lat], [lon1, lat]);
        }
        const xy = pts.map((p) => projection(p));
        const xs = xy.map((p) => p[0]);
        const ys = xy.map((p) => p[1]);
        const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
        k = Math.min(W / (x1 - x0), H / (y1 - y0));
        tx = W / 2 - k * ((x0 + x1) / 2);
        ty = H / 2 - k * ((y0 + y1) / 2);
      }
      g.style.transform = `translate(${tx}px, ${ty}px) scale(${k})`;
      pins.forEach((pin) => {
        pin.style.transform = `translate(${pin.dataset.x}px, ${pin.dataset.y}px) scale(${1 / k})`;
      });
      svg.classList.toggle("is-world", k === 1);
      pop.hide();
    };

    const wire = (attr, fn) => {
      const chips = [...shell.querySelectorAll(`.chip[data-${attr}]`)];
      chips.forEach((chip) =>
        chip.addEventListener("click", () => {
          chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
          fn(chip.dataset[attr]);
        })
      );
    };
    wire("year", (y) => {
      state.year = y;
      applyYear();
    });
    wire("view", setView);
  }

  function makePopover(root) {
    const box = document.createElement("div");
    box.className = "map-pop";
    box.hidden = true;
    box.setAttribute("role", "dialog");
    box.innerHTML = '<button class="close" type="button" aria-label="Close">×</button><h3></h3><ul></ul>';
    root.append(box);
    let opener = null;

    const hide = () => {
      if (box.hidden) return;
      box.hidden = true;
      opener = null;
    };
    box.querySelector(".close").addEventListener("click", () => {
      const back = opener;
      hide();
      back?.focus();
    });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        const back = opener;
        hide();
        back?.focus();
      }
    });
    document.addEventListener("click", (e) => {
      if (!box.hidden && !box.contains(e.target) && e.target !== opener) hide();
    });

    const show = (id, list, x, y, from) => {
      opener = from;
      box.querySelector("h3").textContent = names[id];
      box.setAttribute("aria-label", `Trips in ${names[id]}`);
      const ul = box.querySelector("ul");
      ul.replaceChildren(
        ...list.map((t) => {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = `/trips/${t.slug}/`;
          const im = document.createElement("img");
          im.src = t.thumb;
          im.alt = "";
          im.width = 56;
          im.height = 56;
          const text = document.createElement("span");
          const strong = document.createElement("strong");
          strong.textContent = t.title;
          const time = document.createElement("time");
          time.dateTime = t.date;
          time.textContent = t.label;
          text.append(strong, time);
          a.append(im, text);
          li.append(a);
          return li;
        })
      );
      box.hidden = false;
      const bw = box.offsetWidth;
      const bh = box.offsetHeight;
      const rw = root.clientWidth;
      const rh = root.clientHeight;
      const left = Math.max(4, Math.min(x + 12, rw - bw - 4));
      const top = y + 12 + bh > rh ? Math.max(4, y - bh - 12) : y + 12;
      box.style.left = `${left}px`;
      box.style.top = `${top}px`;
      box.querySelector("a")?.focus({ preventScroll: true });
    };

    return { show, hide };
  }
})();
