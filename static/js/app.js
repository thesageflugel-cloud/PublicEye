document.addEventListener("DOMContentLoaded", () => {
    const locationButton = document.querySelector("[data-fill-location]");
    if (!locationButton) {
        return;
    }

    locationButton.addEventListener("click", () => {
        if (!navigator.geolocation) {
            window.alert("Geolocation is not supported in this browser.");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const latitude = document.getElementById("latitude");
                const longitude = document.getElementById("longitude");
                if (latitude) {
                    latitude.value = position.coords.latitude.toFixed(6);
                }
                if (longitude) {
                    longitude.value = position.coords.longitude.toFixed(6);
                }
            },
            () => {
                window.alert("Unable to fetch your location right now.");
            }
        );
    });
});
