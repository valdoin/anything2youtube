let playlistData = [];
let currentIndex = 0;
let isShuffle = false;
let isLoop = false;
const trackCache = new Map();

const audioPlayerElement = document.getElementById('audioPlayer');
const player = new Plyr(audioPlayerElement, {
    controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume'],
    seekTime: 10
});

const albumArt = document.getElementById('albumArt');
const btnPrev = document.getElementById('btnPrev');
const btnNext = document.getElementById('btnNext');
const btnShuffle = document.getElementById('btnShuffle');
const btnLoop = document.getElementById('btnLoop');
const mainContent = document.getElementById('main-content');
const ytLinkBtn = document.getElementById('yt-link');

const pickr = Pickr.create({
    el: '.color-picker-container',
    theme: 'nano',
    default: '#FF0000',
    components: {
        preview: true, opacity: false, hue: true,
        interaction: { hex: true, rgba: false, input: true, save: false }
    }
});

pickr.on('change', (color, source, instance) => {
    const newColor = color.toHEXA().toString();
    document.documentElement.style.setProperty('--accent-color', newColor);
    instance.applyColor(true); 
});

player.on('ended', () => {
    if (isLoop) {
        player.restart();
        player.play();
    } else {
        playNext();
    }
});

audioPlayerElement.onerror = function() {
    setTimeout(playNext, 1000);
};

function updateButtons() {
    btnPrev.disabled = playlistData.length === 0;
    btnNext.disabled = playlistData.length === 0;
    btnShuffle.disabled = playlistData.length === 0;
    btnLoop.disabled = playlistData.length === 0;
}

function toggleShuffle() {
    isShuffle = !isShuffle;
    btnShuffle.classList.toggle('active', isShuffle);
}

function toggleLoop() {
    isLoop = !isLoop;
    btnLoop.classList.toggle('active', isLoop);
}

async function loadPlaylist() {
    const url = document.getElementById('playlistURL').value;
    if(!url) return alert("Missing link");
    
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
        updateButtons();
        trackCache.clear();
        
        if(playlistData.length > 0) playTrack(0);
        
    } catch(e) { 
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
    
    ytLinkBtn.classList.add('hidden');
    albumArt.style.display = "none";
    albumArt.src = "";

    try {
        let videoData;

        if (trackCache.has(track.query)) {
            videoData = trackCache.get(track.query);
        } else {
            const res = await fetch('/api/find_video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ query: track.query })
            });
            videoData = await res.json();
        }

        if(videoData.audioUrl) {
            if (!trackCache.has(track.query)) {
                trackCache.set(track.query, videoData);
            }

            if (videoData.thumbnail) {
                albumArt.src = videoData.thumbnail;
                albumArt.style.display = "block";
            }

            if (videoData.youtubeUrl) {
                ytLinkBtn.href = videoData.youtubeUrl;
                ytLinkBtn.classList.remove('hidden'); 
            }
            
            player.source = {
                type: 'audio',
                title: track.title,
                sources: [{ src: videoData.audioUrl, type: 'audio/mp4' }],
            };
            
            await player.play();
            if(statusEl) statusEl.innerText = "playing...";

            preloadNextTrack(index);

        } else {
            if(statusEl) statusEl.innerText = "error";
            setTimeout(playNext, 2000);
        }
    } catch(e) {
        playNext();
    }
}

async function preloadNextTrack(currentIndex) {
    let nextIndex;
    if (isShuffle) {
        if (playlistData.length > 1) {
             nextIndex = (currentIndex + 1) % playlistData.length; 
        }
    } else {
        if (currentIndex < playlistData.length - 1) {
            nextIndex = currentIndex + 1;
        } else if (isLoop) {
            nextIndex = 0;
        }
    }

    if (nextIndex !== undefined) {
        const nextTrack = playlistData[nextIndex];
        if (!trackCache.has(nextTrack.query)) {
            try {
                const res = await fetch('/api/find_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ query: nextTrack.query })
                });
                const data = await res.json();
                if (data.audioUrl) {
                    trackCache.set(nextTrack.query, data);
                }
            } catch (e) {
            }
        }
    }
}

function playNext() {
    if (isShuffle) {
        let randomIndex = Math.floor(Math.random() * playlistData.length);
        while (randomIndex === currentIndex && playlistData.length > 1) {
            randomIndex = Math.floor(Math.random() * playlistData.length);
        }
        playTrack(randomIndex);
    } else {
        if (currentIndex < playlistData.length - 1) {
            playTrack(currentIndex + 1);
        } else if (isLoop && playlistData.length > 1) {
             playTrack(0);
        }
    }
}

function playPrevious() {
    if (currentIndex > 0) {
        playTrack(currentIndex - 1);
    }
}