let playlistData = [];
let currentIndex = 0;

const audioPlayerElement = document.getElementById('audioPlayer');
const player = new Plyr(audioPlayerElement, {
    controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume'],
    seekTime: 10
});

const albumArt = document.getElementById('albumArt');
const btnPrev = document.getElementById('btnPrev');
const btnNext = document.getElementById('btnNext');
const mainContent = document.getElementById('main-content');

const pickr = Pickr.create({
    el: '.color-picker-container',
    theme: 'nano',
    default: '#FF0000',
    
    components: {
        preview: true,
        opacity: false,
        hue: true,

        interaction: {
            hex: true,
            rgba: false,
            input: true,
            save: false
        }
    }
});

pickr.on('change', (color, source, instance) => {
    const newColor = color.toHEXA().toString();
    document.documentElement.style.setProperty('--accent-color', newColor);
    instance.applyColor(true); 
});

player.on('ended', () => {
    playNext();
});

audioPlayerElement.onerror = function() {
    setTimeout(playNext, 1000);
};

function updateButtons() {
    btnPrev.disabled = playlistData.length === 0 || currentIndex === 0;
    btnNext.disabled = playlistData.length === 0 || currentIndex === playlistData.length - 1;
}

async function loadPlaylist() {
    const url = document.getElementById('playlistURL').value;
    if(!url) return alert("missing link");
    
    document.getElementById('btnLoad').disabled = true;
    
    try {
        const res = await fetch('/api/get_tracks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        
        if(data.error) { 
            alert(data.error); 
            return; 
        }
        
        playlistData = data.tracks;
        renderPlaylist();
        
        mainContent.classList.remove('hidden');
        
        if(playlistData.length > 0) playTrack(0);
        
    } catch(e) { 
        console.error(e);
        alert('server error');
    } finally { 
        document.getElementById('btnLoad').disabled = false; 
    }
}

function renderPlaylist() {
    const list = document.getElementById('playlist');
    list.innerHTML = "";
    playlistData.forEach((t, i) => {
        const li = document.createElement('li');
        li.className = "track-item";
        li.id = `track-${i}`;
        li.innerHTML = `<span>${t.title} - ${t.artist}</span> <span class="status" id="status-${i}"></span>`;
        li.onclick = () => playTrack(i);
        list.appendChild(li);
    });
}

async function playTrack(index) {
    if(index < 0 || index >= playlistData.length) return;
    
    currentIndex = index;
    const track = playlistData[index];
    
    updateButtons();

    document.querySelectorAll('.track-item').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.status').forEach(e => e.innerText = ""); 

    const activeItem = document.getElementById(`track-${index}`);
    if(activeItem) {
        activeItem.classList.add('active');
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    const statusEl = document.getElementById(`status-${index}`);
    if(statusEl) statusEl.innerText = "loading...";
    
    document.getElementById('current-title').innerText = track.title;
    document.getElementById('current-artist').innerText = track.artist;
    
    document.title = `${track.title} • ${track.artist}`;
    
    albumArt.style.display = "none";
    albumArt.src = "";

    try {
        const res = await fetch('/api/find_video', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query: track.query })
        });
        const data = await res.json();

        if(data.audioUrl) {
            if (data.thumbnail) {
                albumArt.src = data.thumbnail;
                albumArt.style.display = "block";
            }
            
            player.source = {
                type: 'audio',
                title: track.title,
                sources: [
                    {
                        src: data.audioUrl,
                        type: 'audio/mp4',
                    },
                ],
            };
            
            player.play();
            if(statusEl) statusEl.innerText = "playing...";
        } else {
            if(statusEl) statusEl.innerText = "error";
            setTimeout(playNext, 2000);
        }
    } catch(e) {
        console.error(e);
        playNext();
    }
}

function playNext() {
    playTrack(currentIndex + 1);
}

function playPrevious() {
    playTrack(currentIndex - 1);
}