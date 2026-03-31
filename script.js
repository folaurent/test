// ========================================
// Snake Arcade — Jeu Snake moderne
// ========================================

(() => {
  "use strict";

  // ---- Éléments DOM ----
  const menuScreen = document.getElementById("menu");
  const gameScreen = document.getElementById("game");
  const gameoverScreen = document.getElementById("gameover");
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  const pauseOverlay = document.getElementById("pause-overlay");

  const scoreEl = document.getElementById("score");
  const bestScoreEl = document.getElementById("best-score");
  const menuBestEl = document.getElementById("menu-best");
  const finalScoreEl = document.getElementById("final-score");
  const finalBestEl = document.getElementById("final-best");
  const modeDisplay = document.getElementById("mode-display");

  const btnPlay = document.getElementById("btn-play");
  const btnReplay = document.getElementById("btn-replay");
  const btnMenu = document.getElementById("btn-menu");
  const btnResume = document.getElementById("btn-resume");
  const btnQuit = document.getElementById("btn-quit");
  const btnWalls = document.getElementById("btn-walls");
  const btnNoWalls = document.getElementById("btn-nowalls");

  // ---- Configuration ----
  const GRID_SIZE = 20; // Nombre de cellules par côté
  const BASE_SPEED = 150; // Intervalle initial en ms
  const MIN_SPEED = 60; // Vitesse max (intervalle min)
  const SPEED_INCREMENT = 3; // Réduction d'intervalle par fruit mangé

  // Types de bonus
  const BONUS_TYPES = {
    normal: { color: "#00e676", points: 1, flash: "flash" },
    gold: { color: "#ffab00", points: 3, flash: "flash-gold" },
    purple: { color: "#d500f9", points: 5, flash: "flash-purple" },
  };

  // ---- État du jeu ----
  let cellSize, canvasSize;
  let snake, direction, nextDirection;
  let food, foodType;
  let score, bestScore, speed;
  let gameLoop, paused, running;
  let wallMode = true;
  let particles = [];

  // ---- Initialisation du canvas ----
  function resizeCanvas() {
    const maxSize = Math.min(window.innerWidth - 40, 600);
    canvasSize = Math.floor(maxSize / GRID_SIZE) * GRID_SIZE;
    cellSize = canvasSize / GRID_SIZE;
    canvas.width = canvasSize;
    canvas.height = canvasSize;
  }

  // ---- Gestion des écrans ----
  function showScreen(screen) {
    [menuScreen, gameScreen, gameoverScreen].forEach((s) => s.classList.add("hidden"));
    screen.classList.remove("hidden");
  }

  // ---- Meilleur score (localStorage) ----
  function loadBestScore() {
    bestScore = parseInt(localStorage.getItem("snake-best") || "0", 10);
    menuBestEl.textContent = bestScore;
    bestScoreEl.textContent = bestScore;
  }

  function saveBestScore() {
    if (score > bestScore) {
      bestScore = score;
      localStorage.setItem("snake-best", bestScore);
    }
  }

  // ---- Génération de nourriture ----
  function randomCell() {
    return Math.floor(Math.random() * GRID_SIZE);
  }

  function spawnFood() {
    // Position libre (pas sur le serpent)
    let pos;
    do {
      pos = { x: randomCell(), y: randomCell() };
    } while (snake.some((s) => s.x === pos.x && s.y === pos.y));

    food = pos;

    // Type de bonus aléatoire
    const roll = Math.random();
    if (roll < 0.1) foodType = "purple";
    else if (roll < 0.3) foodType = "gold";
    else foodType = "normal";
  }

  // ---- Particules d'effet ----
  function emitParticles(x, y, color) {
    for (let i = 0; i < 8; i++) {
      particles.push({
        x: x * cellSize + cellSize / 2,
        y: y * cellSize + cellSize / 2,
        vx: (Math.random() - 0.5) * 6,
        vy: (Math.random() - 0.5) * 6,
        life: 1,
        color,
      });
    }
  }

  function updateParticles() {
    particles = particles.filter((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.life -= 0.04;
      return p.life > 0;
    });
  }

  function drawParticles() {
    particles.forEach((p) => {
      ctx.globalAlpha = p.life;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  // ---- Flash du canvas ----
  function flashCanvas(className) {
    canvas.classList.remove("flash", "flash-gold", "flash-purple");
    // Force reflow pour relancer l'animation
    void canvas.offsetWidth;
    canvas.classList.add(className);
    setTimeout(() => canvas.classList.remove(className), 400);
  }

  // ---- Dessin ----
  function drawGrid() {
    ctx.fillStyle = "#0d0d18";
    ctx.fillRect(0, 0, canvasSize, canvasSize);

    // Grille subtile
    ctx.strokeStyle = "rgba(255, 255, 255, 0.02)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= GRID_SIZE; i++) {
      const pos = i * cellSize;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, canvasSize);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(canvasSize, pos);
      ctx.stroke();
    }
  }

  function drawSnake() {
    snake.forEach((segment, i) => {
      const x = segment.x * cellSize;
      const y = segment.y * cellSize;
      const pad = 1;

      // Dégradé de la tête à la queue
      const ratio = 1 - i / snake.length;
      const g = Math.floor(180 + 50 * ratio);
      ctx.fillStyle = i === 0 ? "#00e676" : `rgb(0, ${g}, ${Math.floor(60 + 40 * ratio)})`;

      // Coins arrondis pour un look moderne
      const r = cellSize * 0.2;
      const w = cellSize - pad * 2;
      ctx.beginPath();
      ctx.moveTo(x + pad + r, y + pad);
      ctx.lineTo(x + pad + w - r, y + pad);
      ctx.quadraticCurveTo(x + pad + w, y + pad, x + pad + w, y + pad + r);
      ctx.lineTo(x + pad + w, y + pad + w - r);
      ctx.quadraticCurveTo(x + pad + w, y + pad + w, x + pad + w - r, y + pad + w);
      ctx.lineTo(x + pad + r, y + pad + w);
      ctx.quadraticCurveTo(x + pad, y + pad + w, x + pad, y + pad + w - r);
      ctx.lineTo(x + pad, y + pad + r);
      ctx.quadraticCurveTo(x + pad, y + pad, x + pad + r, y + pad);
      ctx.fill();

      // Yeux sur la tête
      if (i === 0) {
        ctx.fillStyle = "#0a0a0f";
        const eyeSize = cellSize * 0.15;
        const cx = x + cellSize / 2;
        const cy = y + cellSize / 2;
        let ex1, ey1, ex2, ey2;

        if (direction.x === 1) { ex1 = cx + 4; ey1 = cy - 4; ex2 = cx + 4; ey2 = cy + 4; }
        else if (direction.x === -1) { ex1 = cx - 4; ey1 = cy - 4; ex2 = cx - 4; ey2 = cy + 4; }
        else if (direction.y === -1) { ex1 = cx - 4; ey1 = cy - 4; ex2 = cx + 4; ey2 = cy - 4; }
        else { ex1 = cx - 4; ey1 = cy + 4; ex2 = cx + 4; ey2 = cy + 4; }

        ctx.beginPath();
        ctx.arc(ex1, ey1, eyeSize, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(ex2, ey2, eyeSize, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  function drawFood() {
    const bonus = BONUS_TYPES[foodType];
    const x = food.x * cellSize + cellSize / 2;
    const y = food.y * cellSize + cellSize / 2;
    const radius = cellSize * 0.35;

    // Lueur
    const glow = ctx.createRadialGradient(x, y, radius * 0.3, x, y, radius * 2.5);
    glow.addColorStop(0, bonus.color + "40");
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(
      food.x * cellSize - cellSize,
      food.y * cellSize - cellSize,
      cellSize * 3,
      cellSize * 3
    );

    // Fruit
    ctx.fillStyle = bonus.color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // Reflet
    ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
    ctx.beginPath();
    ctx.arc(x - radius * 0.25, y - radius * 0.25, radius * 0.3, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawWalls() {
    if (!wallMode) return;
    ctx.strokeStyle = "#ff1744";
    ctx.lineWidth = 3;
    ctx.strokeRect(1.5, 1.5, canvasSize - 3, canvasSize - 3);
  }

  function draw() {
    drawGrid();
    drawWalls();
    drawFood();
    drawSnake();
    updateParticles();
    drawParticles();
  }

  // ---- Logique du jeu ----
  function initGame() {
    resizeCanvas();
    const mid = Math.floor(GRID_SIZE / 2);
    snake = [
      { x: mid, y: mid },
      { x: mid - 1, y: mid },
      { x: mid - 2, y: mid },
    ];
    direction = { x: 1, y: 0 };
    nextDirection = { x: 1, y: 0 };
    score = 0;
    speed = BASE_SPEED;
    paused = false;
    running = true;
    particles = [];

    scoreEl.textContent = score;
    loadBestScore();
    modeDisplay.textContent = wallMode ? "Mode : Murs" : "Mode : Sans murs";

    spawnFood();
    draw();
  }

  function move() {
    direction = { ...nextDirection };
    const head = { x: snake[0].x + direction.x, y: snake[0].y + direction.y };

    // Gestion des bords
    if (wallMode) {
      if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
        gameOver();
        return;
      }
    } else {
      // Traversée des murs
      head.x = (head.x + GRID_SIZE) % GRID_SIZE;
      head.y = (head.y + GRID_SIZE) % GRID_SIZE;
    }

    // Collision avec soi-même
    if (snake.some((s) => s.x === head.x && s.y === head.y)) {
      gameOver();
      return;
    }

    snake.unshift(head);

    // Manger la nourriture
    if (head.x === food.x && head.y === food.y) {
      const bonus = BONUS_TYPES[foodType];
      score += bonus.points;
      scoreEl.textContent = score;

      // Effets visuels
      emitParticles(food.x, food.y, bonus.color);
      flashCanvas(bonus.flash);

      // Accélération progressive
      speed = Math.max(MIN_SPEED, speed - SPEED_INCREMENT * bonus.points);

      spawnFood();
      restartLoop();
    } else {
      snake.pop();
    }

    draw();
  }

  function restartLoop() {
    clearInterval(gameLoop);
    gameLoop = setInterval(move, speed);
  }

  function gameOver() {
    running = false;
    clearInterval(gameLoop);
    saveBestScore();
    finalScoreEl.textContent = score;
    finalBestEl.textContent = bestScore;
    showScreen(gameoverScreen);
  }

  function togglePause() {
    if (!running) return;
    paused = !paused;
    if (paused) {
      clearInterval(gameLoop);
      pauseOverlay.classList.remove("hidden");
    } else {
      pauseOverlay.classList.add("hidden");
      restartLoop();
    }
  }

  // ---- Contrôles clavier ----
  document.addEventListener("keydown", (e) => {
    if (!running) return;

    const key = e.key.toLowerCase();

    // Pause
    if (key === " " || key === "escape" || key === "p") {
      e.preventDefault();
      togglePause();
      return;
    }

    if (paused) return;

    // Directions (flèches + ZQSD)
    const dirMap = {
      arrowup: { x: 0, y: -1 },
      arrowdown: { x: 0, y: 1 },
      arrowleft: { x: -1, y: 0 },
      arrowright: { x: 1, y: 0 },
      z: { x: 0, y: -1 },
      s: { x: 0, y: 1 },
      q: { x: -1, y: 0 },
      d: { x: 1, y: 0 },
      w: { x: 0, y: -1 },
      a: { x: -1, y: 0 },
    };

    const newDir = dirMap[key];
    if (!newDir) return;

    // Empêcher le demi-tour
    if (newDir.x !== -direction.x || newDir.y !== -direction.y) {
      nextDirection = newDir;
    }
    e.preventDefault();
  });

  // ---- Événements UI ----
  btnPlay.addEventListener("click", () => {
    showScreen(gameScreen);
    initGame();
    restartLoop();
  });

  btnReplay.addEventListener("click", () => {
    showScreen(gameScreen);
    initGame();
    restartLoop();
  });

  btnMenu.addEventListener("click", () => {
    loadBestScore();
    showScreen(menuScreen);
  });

  btnResume.addEventListener("click", togglePause);

  btnQuit.addEventListener("click", () => {
    paused = false;
    running = false;
    clearInterval(gameLoop);
    pauseOverlay.classList.add("hidden");
    loadBestScore();
    showScreen(menuScreen);
  });

  // Toggle mode murs/sans murs
  btnWalls.addEventListener("click", () => {
    wallMode = true;
    btnWalls.classList.add("active");
    btnNoWalls.classList.remove("active");
  });

  btnNoWalls.addEventListener("click", () => {
    wallMode = false;
    btnNoWalls.classList.add("active");
    btnWalls.classList.remove("active");
  });

  // Redimensionnement
  window.addEventListener("resize", () => {
    resizeCanvas();
    if (running && !paused) draw();
  });

  // ---- Démarrage ----
  resizeCanvas();
  loadBestScore();
})();
