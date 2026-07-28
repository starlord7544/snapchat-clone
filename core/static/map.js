navigator.geolocation.getCurrentPosition(
  (position) => {
    const map = new mapboxgl.Map({
      accessToken: window.MAPBOX_ACCESS_TOKEN || "",
      container: "map",
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      projection: "globe",
      zoom: 16,
      center: [position.coords.longitude, position.coords.latitude],
    });

    map.addControl(new mapboxgl.NavigationControl());
    map.scrollZoom.disable();

    const imageMarker = document.createElement("img");
    imageMarker.src = "http://localhost:8000/media/snaps/default.jpg";
    imageMarker.style.width = "40px";
    imageMarker.style.height = "40px";

    imageMarker.style.borderRadius = "100%";

    new mapboxgl.Marker({ color: "#e63946", element: imageMarker })
      .setLngLat([78.75773, 28.8709])
      .addTo(map);
    new mapboxgl.Marker({ color: "#3978e6" }).setLngLat([77.69673, 27.57815]).addTo(map);
  },
  () => {
    alert("error");
  },
);
