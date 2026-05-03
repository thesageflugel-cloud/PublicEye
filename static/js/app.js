const DEFAULT_CITY = { lat: 23.2599, lng: 77.4126 };

function setFieldValue(selectorOrElement, value) {
    const element = typeof selectorOrElement === "string"
        ? document.querySelector(selectorOrElement)
        : selectorOrElement;

    if (element) {
        element.value = value;
    }
}

function parseCoordinate(value) {
    if (!value) {
        return null;
    }

    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function loadGoogleMaps(apiKey) {
    if (!apiKey) {
        return Promise.resolve(null);
    }

    if (window.google?.maps) {
        return Promise.resolve(window.google.maps);
    }

    if (window.__publicEyeGoogleMapsPromise) {
        return window.__publicEyeGoogleMapsPromise;
    }

    window.__publicEyeGoogleMapsPromise = new Promise((resolve, reject) => {
        const existingScript = document.querySelector("[data-google-maps-loader]");
        if (existingScript) {
            existingScript.addEventListener("load", () => resolve(window.google?.maps ?? null));
            existingScript.addEventListener("error", reject);
            return;
        }

        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places`;
        script.async = true;
        script.defer = true;
        script.dataset.googleMapsLoader = "true";
        script.onload = () => resolve(window.google?.maps ?? null);
        script.onerror = reject;
        document.head.appendChild(script);
    });

    return window.__publicEyeGoogleMapsPromise;
}

function updateStatus(statusNode, message) {
    if (statusNode) {
        statusNode.textContent = message;
    }
}

function buildFallbackMap(mapNode, message) {
    mapNode.classList.add("is-empty");
    mapNode.innerHTML = `<div class="map-fallback">${message}</div>`;
}

function initializeLocationButtons({ latitudeField, longitudeField, statusNode }) {
    const locateButton = document.querySelector("[data-fill-location]");
    const clearButton = document.querySelector("[data-clear-location]");

    if (locateButton) {
        locateButton.addEventListener("click", () => {
            if (!navigator.geolocation) {
                window.alert("Geolocation is not supported in this browser.");
                return;
            }

            updateStatus(statusNode, "Fetching your current location...");

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const latitude = position.coords.latitude.toFixed(6);
                    const longitude = position.coords.longitude.toFixed(6);
                    setFieldValue(latitudeField, latitude);
                    setFieldValue(longitudeField, longitude);
                    document.dispatchEvent(new CustomEvent("publiceye:location-picked", {
                        detail: { lat: Number.parseFloat(latitude), lng: Number.parseFloat(longitude) }
                    }));
                    updateStatus(statusNode, "Coordinates captured. You can refine the pin by clicking the map.");
                },
                () => {
                    updateStatus(statusNode, "Unable to fetch your location right now. You can still enter the landmark and coordinates manually.");
                    window.alert("Unable to fetch your location right now.");
                }
            );
        });
    }

    return { clearButton };
}

async function initComplaintFormMap() {
    const mapNode = document.querySelector("[data-complaint-map]");
    if (!mapNode) {
        return;
    }

    const statusNode = document.querySelector("[data-map-status]");
    const latitudeField = document.querySelector(mapNode.dataset.latTarget);
    const longitudeField = document.querySelector(mapNode.dataset.lngTarget);
    const locationField = document.querySelector(mapNode.dataset.locationTarget);
    const apiKey = document.body.dataset.googleMapsKey || "";
    const { clearButton } = initializeLocationButtons({ latitudeField, longitudeField, statusNode });

    const initialLat = parseCoordinate(latitudeField?.value);
    const initialLng = parseCoordinate(longitudeField?.value);

    if (!apiKey) {
        buildFallbackMap(mapNode, "Add GOOGLE_MAPS_API_KEY to enable clickable Google Maps pin placement.");
        updateStatus(statusNode, "Map API key not configured yet. Manual landmark and coordinates still work.");
        if (clearButton) {
            clearButton.addEventListener("click", () => {
                setFieldValue(latitudeField, "");
                setFieldValue(longitudeField, "");
                document.dispatchEvent(new CustomEvent("publiceye:location-cleared"));
                updateStatus(statusNode, "Location fields cleared.");
            });
        }
        return;
    }

    try {
        await loadGoogleMaps(apiKey);

        const center = initialLat !== null && initialLng !== null
            ? { lat: initialLat, lng: initialLng }
            : DEFAULT_CITY;

        const map = new google.maps.Map(mapNode, {
            center,
            zoom: initialLat !== null && initialLng !== null ? 15 : 12,
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: false,
            styles: [
                { elementType: "geometry", stylers: [{ color: "#102033" }] },
                { elementType: "labels.text.fill", stylers: [{ color: "#d9ebff" }] },
                { elementType: "labels.text.stroke", stylers: [{ color: "#102033" }] },
                { featureType: "road", elementType: "geometry", stylers: [{ color: "#1c3550" }] },
                { featureType: "water", elementType: "geometry", stylers: [{ color: "#0c3a4e" }] },
                { featureType: "poi", elementType: "geometry", stylers: [{ color: "#18354a" }] }
            ]
        });

        mapNode.classList.add("is-live");

        let marker = null;

        function updateMarker(latLng, shouldPan = true) {
            setFieldValue(latitudeField, latLng.lat().toFixed(6));
            setFieldValue(longitudeField, latLng.lng().toFixed(6));

            if (!marker) {
                marker = new google.maps.Marker({
                    map,
                    position: latLng,
                    draggable: true,
                    animation: google.maps.Animation.DROP
                });

                marker.addListener("dragend", (event) => {
                    updateMarker(event.latLng, false);
                });
            } else {
                marker.setPosition(latLng);
            }

            if (shouldPan) {
                map.panTo(latLng);
                map.setZoom(16);
            }

            updateStatus(statusNode, "Pin updated. The complaint will be saved with these coordinates.");
        }

        if (initialLat !== null && initialLng !== null) {
            updateMarker(new google.maps.LatLng(initialLat, initialLng), false);
        } else {
            updateStatus(statusNode, "Click the map or use your current location to capture coordinates.");
        }

        map.addListener("click", (event) => {
            updateMarker(event.latLng);
        });

        document.addEventListener("publiceye:location-picked", (event) => {
            const { lat, lng } = event.detail;
            updateMarker(new google.maps.LatLng(lat, lng));
        });

        if (clearButton) {
            clearButton.addEventListener("click", () => {
                setFieldValue(latitudeField, "");
                setFieldValue(longitudeField, "");
                if (marker) {
                    marker.setMap(null);
                    marker = null;
                }
                map.panTo(DEFAULT_CITY);
                map.setZoom(12);
                updateStatus(statusNode, "Location fields cleared.");
            });
        }

        document.addEventListener("publiceye:location-cleared", () => {
            setFieldValue(latitudeField, "");
            setFieldValue(longitudeField, "");
            if (marker) {
                marker.setMap(null);
                marker = null;
            }
            map.panTo(DEFAULT_CITY);
            map.setZoom(12);
        });

        if (locationField && google.maps.places?.Autocomplete) {
            const autocomplete = new google.maps.places.Autocomplete(locationField, {
                fields: ["formatted_address", "geometry"],
            });

            autocomplete.addListener("place_changed", () => {
                const place = autocomplete.getPlace();
                if (!place?.geometry?.location) {
                    return;
                }

                if (place.formatted_address) {
                    locationField.value = place.formatted_address;
                }
                updateMarker(place.geometry.location);
            });
        }
    } catch (error) {
        console.error("Failed to load Google Maps", error);
        buildFallbackMap(mapNode, "Google Maps could not load in this browser session. Manual location fields are still available.");
        updateStatus(statusNode, "Google Maps did not load. You can still submit a landmark and manual coordinates.");
    }
}

async function initComplaintDetailMap() {
    const mapNode = document.querySelector("[data-complaint-map-display]");
    if (!mapNode) {
        return;
    }

    const apiKey = document.body.dataset.googleMapsKey || "";
    const lat = parseCoordinate(mapNode.dataset.lat);
    const lng = parseCoordinate(mapNode.dataset.lng);
    const label = mapNode.dataset.locationLabel || "Complaint location";

    if (lat === null || lng === null) {
        buildFallbackMap(mapNode, "No coordinates were captured for this complaint yet.");
        return;
    }

    if (!apiKey) {
        buildFallbackMap(mapNode, "Add GOOGLE_MAPS_API_KEY to render the live complaint map here.");
        return;
    }

    try {
        await loadGoogleMaps(apiKey);

        const center = { lat, lng };
        const map = new google.maps.Map(mapNode, {
            center,
            zoom: 15,
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: false,
            styles: [
                { elementType: "geometry", stylers: [{ color: "#102033" }] },
                { elementType: "labels.text.fill", stylers: [{ color: "#d9ebff" }] },
                { elementType: "labels.text.stroke", stylers: [{ color: "#102033" }] }
            ]
        });

        new google.maps.Marker({
            map,
            position: center,
            title: label,
        });

        mapNode.classList.add("is-live");
    } catch (error) {
        console.error("Failed to load Google Maps", error);
        buildFallbackMap(mapNode, "Google Maps could not load for this complaint view.");
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await initComplaintFormMap();
    await initComplaintDetailMap();
});
