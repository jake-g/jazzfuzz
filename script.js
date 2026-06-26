// Setup and interaction handlers for Jazz Fuzz site
$(document).ready(function () {
  // Collapse details handler (Global)
  $("#collapse-main").click(function () {
    var button = $(this);
    button.toggleClass("inverted");
    var isCollapsed = button.hasClass("inverted");
    if (isCollapsed) {
      $("main").slideUp(150);
      $(".toggle-details-btn").text("Expand");
      button.text("Expand");
    } else {
      $("main").slideDown(150);
      $(".toggle-details-btn").text("Collapse");
      button.text("Collapse");
    }
  });

  // Individual toggle details handler
  $("#posts").on("click", ".toggle-details-btn", function () {
    var button = $(this);
    var main = button.closest("article").find("main");
    main.slideToggle(150, function () {
      if (main.is(":visible")) {
        button.text("Collapse");
      } else {
        button.text("Expand");
      }
    });
  });

  // Sort Panel Toggle
  $("#sort-menu-btn").click(function () {
    $(this).toggleClass("active");
    $("#sort-panel").slideToggle(150);
    $("#filter-menu-btn").removeClass("active");
    $("#filter-panel").slideUp(150);
  });

  // Filter Panel Toggle
  $("#filter-menu-btn").click(function () {
    $(this).toggleClass("active");
    $("#filter-panel").slideToggle(150);
    $("#sort-menu-btn").removeClass("active");
    $("#sort-panel").slideUp(150);
  });

  // --- SORTING LOGIC ---
  function sortPosts(sortBy) {
    var posts = $("#posts").children("article");
    posts.sort(function (a, b) {
      if (sortBy === "artist") {
        var artistA = $(a)
          .find("header h3:contains('By')")
          .text()
          .trim()
          .split(": ")
          .pop()
          .toUpperCase();
        var artistB = $(b)
          .find("header h3:contains('By')")
          .text()
          .trim()
          .split(": ")
          .pop()
          .toUpperCase();
        if (artistA < artistB) {
          return -1;
        }
        if (artistA > artistB) {
          return 1;
        }
        return 0;
      } else if (sortBy === "year") {
        var yearAStr = $(a).find("header h3:contains('Released:')").text();
        var yearBStr = $(b).find("header h3:contains('Released:')").text();
        var matchA = yearAStr.match(/\d{4}/);
        var matchB = yearBStr.match(/\d{4}/);
        var yearA = matchA ? parseInt(matchA[0], 10) : 0;
        var yearB = matchB ? parseInt(matchB[0], 10) : 0;
        return yearA - yearB;
      } else {
        var popA = parseInt($(a).attr("data-popularity") || "0", 10);
        var popB = parseInt($(b).attr("data-popularity") || "0", 10);
        return popB - popA; // Descending (highest popularity first)
      }
    });
    $("#posts").empty().append(posts);
  }

  // Sort actions click handlers
  $("#sort-popularity-action").click(function (e) {
    e.preventDefault();
    $("#sort-panel a").removeClass("active");
    $(this).addClass("active");
    $("#sort-menu-btn").text("Sort: Popularity v");
    sortPosts("popularity");
  });

  $("#sort-year-action").click(function (e) {
    e.preventDefault();
    $("#sort-panel a").removeClass("active");
    $(this).addClass("active");
    $("#sort-menu-btn").text("Sort: Year v");
    sortPosts("year");
  });

  $("#sort-artist-action").click(function (e) {
    e.preventDefault();
    $("#sort-panel a").removeClass("active");
    $(this).addClass("active");
    $("#sort-menu-btn").text("Sort: Artist v");
    sortPosts("artist");
  });

  // --- FILTERING LOGIC ---
  var activeDecades = new Set();
  var activeGenres = new Set();
  var activeArtists = new Set();

  function applyFilters() {
    $("#posts").children("article").each(function () {
      var article = $(this);

      // Decade match
      var matchDecade = true;
      if (activeDecades.size > 0) {
        var yearStr = article.find("header h3:contains('Released:')").text();
        var match = yearStr.match(/\d{4}/);
        if (match) {
          var dec = Math.floor(parseInt(match[0], 10) / 10) * 10 + "s";
          matchDecade = activeDecades.has(dec);
        } else {
          matchDecade = false;
        }
      }

      // Genre match (matches if the article contains ANY of the active genres!)
      var matchGenre = true;
      if (activeGenres.size > 0) {
        var genreStr = article
          .find("header h3:contains('Genre:')")
          .text()
          .split(": ")
          .pop()
          .toLowerCase();

        matchGenre = false;
        activeGenres.forEach(function (g) {
          if (genreStr.indexOf(g) !== -1) {
            matchGenre = true;
          }
        });
      }

      // Artist match
      var matchArtist = true;
      if (activeArtists.size > 0) {
        var artistStr = article
          .find("header h3:contains('By:')")
          .text()
          .trim()
          .split(": ")
          .pop()
          .toLowerCase();
        matchArtist = activeArtists.has(artistStr);
      }

      article.toggle(matchDecade && matchGenre && matchArtist);
    });
  }

  // Handle filter action click
  $("#filter-panel").on("click", ".filter-action", function (e) {
    e.preventDefault();
    var link = $(this);
    var filterType = link.attr("data-filter-type");
    var filterVal = link.attr("data-filter-val");

    var activeSet;
    var allLink;
    if (filterType === "decade") {
      activeSet = activeDecades;
      allLink = link.closest(".filter-group").find('[data-filter-val="all"]');
    } else if (filterType === "genre") {
      activeSet = activeGenres;
      allLink = link.closest(".filter-group").find('[data-filter-val="all"]');
    } else if (filterType === "artist") {
      activeSet = activeArtists;
      allLink = link.closest(".filter-group").find('[data-filter-val="all"]');
    }

    if (filterVal === "all") {
      activeSet.clear();
      link.closest(".filter-group").find(".filter-action").removeClass("active");
      link.addClass("active");
    } else {
      var normalVal = filterVal.toLowerCase();
      if (activeSet.has(normalVal)) {
        activeSet.delete(normalVal);
        link.removeClass("active");
      } else {
        activeSet.add(normalVal);
        link.addClass("active");
      }

      // Deactivate the "All" button
      allLink.removeClass("active");

      // If nothing is selected, reactivate "All"
      if (activeSet.size === 0) {
        allLink.addClass("active");
      }
    }

    applyFilters();
  });

  // --- DYNAMICALLY POPULATE FILTERS FROM DOM ---
  const MAX_GENRES_TO_SHOW = 12;
  const MAX_ARTISTS_TO_SHOW = 12;

  function populateFilters() {
    var decadeCounts = {};
    var genreCounts = {};
    var artistCounts = {};

    $("#posts").children("article").each(function () {
      var article = $(this);

      // 1. Decades
      var yearStr = article.find("header h3:contains('Released:')").text();
      var match = yearStr.match(/\d{4}/);
      if (match) {
        var dec = Math.floor(parseInt(match[0], 10) / 10) * 10 + "s";
        decadeCounts[dec] = (decadeCounts[dec] || 0) + 1;
      }

      // 2. Genres
      var genreStr = article
        .find("header h3:contains('Genre:')")
        .text()
        .split(": ")
        .pop();
      if (genreStr) {
        var parts = genreStr.split(",");
        parts.forEach(function (p) {
          var g = p.trim();
          if (g) {
            genreCounts[g] = (genreCounts[g] || 0) + 1;
          }
        });
      }

      // 3. Artists
      var artistStr = article
        .find("header h3:contains('By:')")
        .text()
        .trim()
        .split(": ")
        .pop();
      if (artistStr) {
        artistCounts[artistStr] = (artistCounts[artistStr] || 0) + 1;
      }
    });

    // Populate Decades
    var sortedDecades = Object.keys(decadeCounts).sort();
    sortedDecades.forEach(function (dec) {
      $("#decade-filters").append(
        '<a href="#" class="filter-action" data-filter-type="decade" data-filter-val="' +
        dec +
        '">' +
        dec +
        ' <span style="opacity: 0.5; font-size: 9px; margin-left: 2px;">(' +
        decadeCounts[dec] +
        ")</span>" +
        "</a>"
      );
    });

    // Populate Genres (Sorted by count descending, showing max MAX_GENRES_TO_SHOW)
    var sortedGenres = Object.keys(genreCounts)
      .sort(function (a, b) {
        return genreCounts[b] - genreCounts[a];
      })
      .slice(0, MAX_GENRES_TO_SHOW);
    sortedGenres.forEach(function (g) {
      $("#genre-filters").append(
        '<a href="#" class="filter-action" data-filter-type="genre" data-filter-val="' +
        g +
        '">' +
        g +
        ' <span style="opacity: 0.5; font-size: 9px; margin-left: 2px;">(' +
        genreCounts[g] +
        ")</span>" +
        "</a>"
      );
    });

    // Populate Artists (Sorted by count descending, showing max MAX_ARTISTS_TO_SHOW)
    var sortedArtists = Object.keys(artistCounts)
      .sort(function (a, b) {
        return artistCounts[b] - artistCounts[a];
      })
      .slice(0, MAX_ARTISTS_TO_SHOW);
    sortedArtists.forEach(function (a) {
      $("#artist-filters").append(
        '<a href="#" class="filter-action" data-filter-type="artist" data-filter-val="' +
        a +
        '">' +
        a +
        ' <span style="opacity: 0.5; font-size: 9px; margin-left: 2px;">(' +
        artistCounts[a] +
        ")</span>" +
        "</a>"
      );
    });
  }

  // Populate dynamic menus
  populateFilters();

  // Initial trigger: Sort by popularity
  sortPosts("popularity");

  // Player logic
  let currentPlayer = null;
  const DEBUG_MODE = true;

  function getPlayerStateName(state) {
    const stateNames = {
      [YT.PlayerState.UNSTARTED]: "Unstarted",
      [YT.PlayerState.ENDED]: "Ended",
      [YT.PlayerState.PLAYING]: "Playing",
      [YT.PlayerState.PAUSED]: "Paused",
      [YT.PlayerState.BUFFERING]: "Buffering",
      [YT.PlayerState.CUED]: "Cued",
    };
    return stateNames[state] || "Unknown";
  }

  function debugLog(...args) {
    if (DEBUG_MODE) {
      console.log(...args);
    }
  }

  $(".playerContainer").each(function () {
    const playerContainer = this;
    const player = playerContainer.querySelector("lite-youtube");

    player.addEventListener("liteYoutubeIframeLoaded", function () {
      const iframe = player.shadowRoot.querySelector("iframe");
      const ytPlayer = new YT.Player(iframe, {
        events: {
          onStateChange: function (event) {
            if (event.data === YT.PlayerState.PLAYING) {
              if (currentPlayer && currentPlayer !== ytPlayer) {
                currentPlayer.pauseVideo();
              }
              currentPlayer = ytPlayer;
            } else if (
              event.data === YT.PlayerState.PAUSED &&
              currentPlayer === ytPlayer
            ) {
              currentPlayer = null;
            }
            debugLog(
              `Video State Change: [${player.videoId}] ${getPlayerStateName(
                event.data
              )}`
            );
          },
          onVolumeChange: function (event) {
            debugLog(
              `Volume Change: [${player.videoId}] ${event.data.volume}% (muted: ${event.data.muted})`
            );
          },
          onPlaybackQualityChange: function (event) {
            debugLog(`Quality Change: [${player.videoId}] ${event.data}`);
          },
          onPlaybackRateChange: function (event) {
            debugLog(`Rate Change: [${player.videoId}] ${event.data}`);
          },
        },
      });
    });
  });
});
