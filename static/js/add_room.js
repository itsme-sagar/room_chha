let currentStep = 1;
const totalSteps = 7;

const progressBar =
document.getElementById("progressBar");

const nextBtn =
document.getElementById("nextBtn");

const prevBtn =
document.getElementById("prevBtn");

const submitBtn =
document.getElementById("submitBtn");

function showStep(step){

    document
    .querySelectorAll(".form-step")
    .forEach(item=>{

        item.classList.remove(
            "active"
        );

    });

    document
    .getElementById(
        "step" + step
    )
    .classList.add("active");

    document
    .querySelectorAll(".wizard-step")
    .forEach((item,index)=>{

        item.classList.toggle(
            "active",
            index < step
        );

    });

    let percent =
    Math.round(
    (step/totalSteps)*100
    );

    if(step === totalSteps){

        percent = 100;

    }

    document.getElementById(
    "progressBar"
    ).style.width =
    percent + "%";

    document.getElementById(
    "progressPercent"
    ).innerText =
    percent + "%";

    const completionScore =
    document.getElementById(
    "completionScore"
    );

    if(completionScore){

        completionScore.innerText =
        percent + "%";

    }

    // document.getElementById(
    // "completionScore"
    // ).innerText =
    // percent + "%";

    if(
    step === 2 &&
    window.roomMap
    ){

        setTimeout(
            function(){

                window.roomMap.invalidateSize();

                window.roomMap.setView(
                    window.roomMap.getCenter(),
                    window.roomMap.getZoom()
                );

            },
            500
        );

    }

    prevBtn.style.display =
    step === 1 ?
    "none" :
    "inline-block";

    nextBtn.style.display =
    step === totalSteps ?
    "none" :
    "inline-block";

    submitBtn.style.display =
    step === totalSteps ?
    "inline-block" :
    "none";
}

nextBtn.addEventListener(
"click",
function(){

    if(currentStep < totalSteps){

        currentStep++;

        showStep(
            currentStep
        );

    }

});

prevBtn.addEventListener(
"click",
function(){

    if(currentStep > 1){

        currentStep--;

        showStep(
            currentStep
        );

    }

});

showStep(1);

document
.querySelectorAll(
".wizard-step"
)
.forEach(stepBtn => {

    stepBtn.addEventListener(
    "click",
    function(){

        currentStep =
        parseInt(
            this.dataset.step
        );

        showStep(
            currentStep
        );

    });

});


const currentLocationBtn =
document.getElementById(
"currentLocationBtn"
);

if(currentLocationBtn){

currentLocationBtn.addEventListener(
"click",
function(){

    navigator.geolocation
    .getCurrentPosition(
    function(position){

        const lat =
        position.coords.latitude;

        const lng =
        position.coords.longitude;

        document.getElementById(
        "latitude"
        ).value = lat;

        document.getElementById(
        "longitude"
        ).value = lng;

        fillAddress(
            lat,
            lng
        );

    });

});

}
document.addEventListener(
"DOMContentLoaded",
function(){

    const mapContainer =
    document.getElementById(
        "roomMap"
    );

    if(!mapContainer) return;

    const map =
    L.map("roomMap")
    .setView(
        [27.7172,85.3240],
        13
    );

    window.roomMap = map;

    let marker;

    window.roomMarker = marker;

    L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution:
        "&copy; OpenStreetMap"
    }
    ).addTo(map);

    map.on(
    "click",
    function(e){

        const lat =
        e.latlng.lat;

        const lng =
        e.latlng.lng;

        if(marker){

            map.removeLayer(
                marker
            );

        }

        marker =
        L.marker(
            [lat,lng]
        ).addTo(map);

        document.getElementById(
        "latitude"
        ).value = lat;

        document.getElementById(
        "longitude"
        ).value = lng;
        fillAddress(
            lat,
            lng
        );

    });

});
const searchInput =
document.getElementById(
"locationSearch"
);

const searchResults =
document.getElementById(
"searchResults"
);

if(searchInput){

searchInput.addEventListener(
"keyup",
async function(){

    const query =
    this.value.trim();

    if(query.length < 3){

        searchResults.innerHTML = "";
        return;

    }

    const response =
    await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&q=${query}`
    );

    const data =
    await response.json();

    searchResults.innerHTML = "";

    data.slice(0,5).forEach(place=>{

        const div =
        document.createElement("div");

        div.className =
        "search-item";

        div.innerHTML =
        "📍 " +
        place.display_name;

        div.addEventListener(
        "click",
        function(){

            selectLocation(
                place
            );

        });

        searchResults.appendChild(
            div
        );

    });

});
}
async function selectLocation(place) {
    const lat = parseFloat(place.lat);
    const lon = parseFloat(place.lon);

    document.getElementById("latitude").value = lat;
    document.getElementById("longitude").value = lon;
    document.getElementById("locationSearch").value = place.display_name;
    document.getElementById("searchResults").innerHTML = "";

    if (window.roomMarker) {
        window.roomMap.removeLayer(window.roomMarker);
    }

    window.roomMarker = L.marker([lat, lon]).addTo(window.roomMap);
    window.roomMap.setView([lat, lon], 16);

    await fillAddress(lat, lng);

    window.roomMap.setView([lat, lng], 16);

    if (window.roomMarker) {
        window.roomMap.removeLayer(window.roomMarker);
    }

    window.roomMarker = L.marker([lat, lng]).addTo(window.roomMap);
}

async function fillAddress(
    lat,
    lon
){

    const response =
    await fetch(
    `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
    );

    const data =
    await response.json();

    const addr =
    data.address;

    document.getElementById(
    "province"
    ).value =
    addr.state || "";

    document.getElementById(
    "district"
    ).value =
    addr.county || "";

    document.getElementById(
    "city"
    ).value =
    addr.city ||
    addr.town ||
    addr.village ||
    "";

    document.getElementById(
    "area"
    ).value =
    addr.suburb ||
    addr.neighbourhood ||
    "";

    document.getElementById(
    "address"
    ).value =
    data.display_name || "";

}
const description =
document.getElementById(
"description"
);

if(description){

description.addEventListener(
"input",
function(){

    document.getElementById(
    "descriptionCount"
    ).innerText =
    this.value.length +
    " / 500";

});
}
// ==========================
// IMAGE UPLOADER
// ==========================

let selectedFiles = [];

const imageInput =
document.getElementById("images");

const preview =
document.getElementById("imagePreview");

const selectBtn =
document.getElementById("selectImagesBtn");

const dropZone =
document.getElementById("dropZone");

if(selectBtn){

    selectBtn.addEventListener(
    "click",
    function(){

        imageInput.click();

    });

}

function renderImages(){

    preview.innerHTML = "";

    selectedFiles.forEach(
    (file,index)=>{

        const reader =
        new FileReader();

        reader.onload =
        function(e){

            const wrapper =
            document.createElement(
            "div"
            );

            wrapper.className =
            "preview-wrapper";

            wrapper.innerHTML = `
                <button
                type="button"
                class="remove-image"
                data-index="${index}">
                    ×
                </button>

                <img
                src="${e.target.result}"
                class="preview-image">
            `;

            preview.appendChild(
                wrapper
            );

        };

        reader.readAsDataURL(
            file
        );

    });

}

if(imageInput){

    imageInput.addEventListener(
    "change",
    function(){

        selectedFiles.push(
            ...Array.from(
                this.files
            )
        );

        renderImages();

    });

}

preview.addEventListener(
"click",
function(e){

    if(
    e.target.classList.contains(
        "remove-image"
    )
    ){

        const index =
        parseInt(
            e.target.dataset.index
        );

        selectedFiles.splice(
            index,
            1
        );

        renderImages();

    }

});
if(dropZone){

dropZone.addEventListener(
"dragover",
function(e){

    e.preventDefault();

    dropZone.classList.add(
        "dragover"
    );

});

dropZone.addEventListener(
"dragleave",
function(){

    dropZone.classList.remove(
        "dragover"
    );

});

dropZone.addEventListener(
"drop",
function(e){

    e.preventDefault();

    dropZone.classList.remove(
        "dragover"
    );

    selectedFiles.push(
        ...Array.from(
            e.dataTransfer.files
        )
    );

    renderImages();

});

}
const previewBtn =
document.getElementById(
"previewBtn"
);

if(previewBtn){

previewBtn.addEventListener(
"click",
function(){

    document.getElementById(
    "previewTitle"
    ).innerText =
    document.querySelector(
    '[name="title"]'
    ).value;

    document.getElementById(
    "previewLocation"
    ).innerText =
    document.querySelector(
    '[name="city"]'
    ).value;

    document.getElementById(
    "previewRent"
    ).innerText =
    "Rs. " +
    document.querySelector(
    '[name="rent"]'
    ).value;

    document.getElementById(
    "previewDescription"
    ).innerText =
    document.querySelector(
    '[name="description"]'
    ).value;

    const firstImage =
    document.querySelector(
    ".preview-image"
    );

    if(firstImage){

        document.getElementById(
        "previewImage"
        ).src =
        firstImage.src;

    }

    new bootstrap.Modal(
    document.getElementById(
    "roomPreviewModal"
    )).show();

});
}


