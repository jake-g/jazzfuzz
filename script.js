// Setup and interaction handlers for Jazz Fuzz site
$(document).ready(function () {
  // Initialize unique article IDs on page load & append Share button next to Expand
  $("#posts").children("article").each(function () {
    var art = $(this);
    var title = art.find("header h2").text().trim();
    var artist = art.find("header h3:contains('By:')").text().replace("By:", "").trim();
    var id = "album-" + (artist + "-" + title).toLowerCase().replace(/[^a-z0-9]+/g, "-");
    art.attr("id", id);

    var expandBtn = art.find(".toggle-details-btn");
    var shareBtn = $('<button class="share-btn" title="Copy link to this album">Share</button>');
    expandBtn.after(shareBtn);
  });

  // Share button click handler
  $("#posts").on("click", ".share-btn", function () {
    var button = $(this);
    var article = button.closest("article");
    var id = article.attr("id");
    var shareUrl = window.location.origin + window.location.pathname + "#" + id;

    navigator.clipboard.writeText(shareUrl).then(function () {
      var originalText = button.text();
      button.text("Copied!");
      setTimeout(function () {
        button.text(originalText);
      }, 1500);
    }).catch(function (err) {
      console.error("Could not copy link to clipboard: ", err);
    });
  });

  // Collapse details handler (Global)
  $("#collapse-main").click(function () {
    var button = $(this);
    button.toggleClass("active");
    var isExpanded = button.hasClass("active");
    if (isExpanded) {
      $("main").slideDown(150);
      $(".toggle-details-btn").text("Collapse");
      button.text("-");
    } else {
      $("main").slideUp(150);
      $(".toggle-details-btn").text("Expand");
      button.text("+");
    }
  });

  $("#scroll-top-link").click(function (e) {
    e.preventDefault();
    $("html, body").animate({ scrollTop: 0 }, 400);
  });

  // Theme Toggle Handler
  $("#theme-toggle-btn").click(function () {
    $("html").toggleClass("light-mode");
    var isLight = $("html").hasClass("light-mode");
    $(this).html(isLight ? "&#9632;" : "&#9633;");
    localStorage.setItem("theme", isLight ? "light" : "dark");
  });

  // Restore saved theme on load
  var savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light") {
    $("html").addClass("light-mode");
    $("#theme-toggle-btn").html("&#9632;");
  }

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
    $("#albums-menu-btn").removeClass("active");
    $("#albums-panel").slideUp(150);
  });

  // Filter Panel Toggle
  $("#filter-menu-btn").click(function () {
    $(this).toggleClass("active");
    $("#filter-panel").slideToggle(150);
    $("#sort-menu-btn").removeClass("active");
    $("#sort-panel").slideUp(150);
    $("#albums-menu-btn").removeClass("active");
    $("#albums-panel").slideUp(150);
  });

  // Albums Panel Toggle
  $("#albums-menu-btn").click(function () {
    $(this).toggleClass("active");
    $("#albums-panel").slideToggle(150);
    $("#sort-menu-btn").removeClass("active");
    $("#sort-panel").slideUp(150);
    $("#filter-menu-btn").removeClass("active");
    $("#filter-panel").slideUp(150);
    if ($(this).hasClass("active")) {
      populateAlbumsTOC();
    }
  });

  // Albums TOC item click handler (Smooth Scroll to Album)
  $("#albums-toc-list").on("click", ".toc-item", function (e) {
    e.preventDefault();
    var targetId = $(this).attr("href");
    var targetOffset = $(targetId).offset().top - 80; // Offset by sticky header height
    $("html, body").animate({ scrollTop: targetOffset }, 400);

    // Auto-close panel
    $("#albums-panel").slideUp(150);
    $("#albums-menu-btn").removeClass("active");
  });

  function splitArtists(artistStr) {
    if (!artistStr) return [];
    var normalized = artistStr
      .replace(/\s+featuring\s+/gi, ", ")
      .replace(/\s+feat\.\s+/gi, ", ")
      .replace(/\s+and\s+/gi, ", ")
      .replace(/\s+&\s+/g, ", ");
    return normalized
      .split(",")
      .map(function (a) { return a.trim(); })
      .filter(function (a) { return a.length > 0; });
  }

  // --- SORTING LOGIC ---
  function sortPosts(sortBy) {
    var posts = $("#posts").children("article");
    posts.sort(function (a, b) {
      if (sortBy === "artist") {
        var rawA = $(a).find("header h3:contains('By')").text().trim().split(": ").pop();
        var rawB = $(b).find("header h3:contains('By')").text().trim().split(": ").pop();
        var subA = splitArtists(rawA);
        var subB = splitArtists(rawB);
        var artistA = (subA[0] || "").toUpperCase();
        var artistB = (subB[0] || "").toUpperCase();
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
        if (popB !== popA) {
          return popB - popA;
        }
        var yearAStr = $(a).find("header h3:contains('Released:')").text();
        var yearBStr = $(b).find("header h3:contains('Released:')").text();
        var matchA = yearAStr.match(/\d{4}/);
        var matchB = yearBStr.match(/\d{4}/);
        var yearA = matchA ? parseInt(matchA[0], 10) : 0;
        var yearB = matchB ? parseInt(matchB[0], 10) : 0;
        return yearB - yearA;
      }
    });
    posts.each(function (index) {
      $(this).css("order", index);
    });
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
          .pop();
        var subArtists = splitArtists(artistStr).map(function (a) {
          return a.toLowerCase();
        });
        matchArtist = false;
        activeArtists.forEach(function (a) {
          if (subArtists.indexOf(a) !== -1) {
            matchArtist = true;
          }
        });
      }

      article.toggle(matchDecade && matchGenre && matchArtist);
    });
    populateAlbumsTOC();
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
  const MAX_GENRES_TO_SHOW = 24;
  const MAX_ARTISTS_TO_SHOW = 24;

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
        var subArtists = splitArtists(artistStr);
        subArtists.forEach(function (a) {
          artistCounts[a] = (artistCounts[a] || 0) + 1;
        });
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

  // Auto-expand and scroll to album if hash anchor is present in URL
  var hash = window.location.hash;
  if (hash) {
    var targetArticle = $(hash);
    if (targetArticle.length) {
      targetArticle.find("main").slideDown(150);
      targetArticle.find(".toggle-details-btn").text("Collapse");
      setTimeout(function () {
        var headerHeight = $("header").outerHeight() || 70;
        var targetOffset = targetArticle.offset().top - (headerHeight + 10);
        $("html, body").animate({ scrollTop: targetOffset }, 200);
      }, 300);
    }
  }

  // Player logic
  let currentPlayer = null;
  let currentArticle = null;
  let isShuffle = false;
  let playbackHistory = [];
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

  function getSortedVisibleArticles() {
    var visible = $("#posts").children("article:visible");
    var sorted = visible.toArray().sort(function (a, b) {
      var orderA = parseInt($(a).css("order") || "0", 10);
      var orderB = parseInt($(b).css("order") || "0", 10);
      return orderA - orderB;
    });
    return $(sorted);
  }

  function updatePlayerControls(isPlaying) {
    $("#play-pause-btn").text(isPlaying ? "||" : ">");
    $("#shuffle-btn").toggleClass("active", isShuffle);
    if (currentArticle) {
      var visibleArticles = getSortedVisibleArticles();
      var currentIndex = visibleArticles.index(currentArticle);
      if (isShuffle) {
        $("#prev-btn").prop("disabled", playbackHistory.length === 0);
        $("#next-btn").prop("disabled", visibleArticles.length <= 1);
      } else {
        $("#prev-btn").prop("disabled", currentIndex <= 0);
        $("#next-btn").prop("disabled", currentIndex >= visibleArticles.length - 1);
      }
    } else {
      $("#prev-btn").prop("disabled", true);
      $("#next-btn").prop("disabled", true);
    }
  }

  function playNextTrack() {
    var visibleArticles = getSortedVisibleArticles();
    if (visibleArticles.length === 0) return;

    if (isShuffle) {
      var candidates = visibleArticles;
      if (currentArticle) {
        candidates = visibleArticles.not(currentArticle);
      }
      if (candidates.length > 0) {
        var randomIndex = Math.floor(Math.random() * candidates.length);
        var randomArticle = candidates.eq(randomIndex);
        playArticle(randomArticle);
      }
    } else {
      if (!currentArticle) {
        playArticle(visibleArticles.first());
      } else {
        var currentIndex = visibleArticles.index(currentArticle);
        if (currentIndex < visibleArticles.length - 1) {
          var nextArticle = visibleArticles.eq(currentIndex + 1);
          playArticle(nextArticle);
        }
      }
    }
  }

  function playPrevTrack() {
    var visibleArticles = getSortedVisibleArticles();
    if (visibleArticles.length === 0) return;

    if (isShuffle) {
      if (playbackHistory.length > 0) {
        var prevArticle = playbackHistory.pop();
        if (prevArticle.is(":visible")) {
          playArticle(prevArticle, false);
        } else {
          playPrevTrack();
        }
      }
    } else {
      if (currentArticle) {
        var currentIndex = visibleArticles.index(currentArticle);
        if (currentIndex > 0) {
          var prevArticle = visibleArticles.eq(currentIndex - 1);
          playArticle(prevArticle);
        }
      }
    }
  }

  function playArticle(article, saveToHistory = true) {
    if (saveToHistory && currentArticle && currentArticle[0] !== article[0]) {
      playbackHistory.push(currentArticle);
    }

    // Collapse other articles' details instantly to avoid layout shifts
    $("#posts").children("article").not(article).find("main").hide();
    $("#posts").children("article").not(article).find(".toggle-details-btn").text("Expand");

    // Expand target article's details instantly
    article.find("main").show();
    article.find(".toggle-details-btn").text("Collapse");

    // Measure the clean offset and scroll to it
    var offset = article.offset().top - 70;
    $("html, body").animate({ scrollTop: offset }, 250);

    var yt = article.find("lite-youtube");
    if (yt.length) {
      var existingPlayer = yt.data("ytPlayer");
      if (existingPlayer && typeof existingPlayer.playVideo === "function") {
        existingPlayer.playVideo();
      } else {
        yt[0].click();
      }
    }
  }

  $("#prev-btn").click(playPrevTrack);
  $("#next-btn").click(playNextTrack);
  $("#play-pause-btn").click(function () {
    if (currentPlayer) {
      var state = currentPlayer.getPlayerState();
      if (state === YT.PlayerState.PLAYING) {
        currentPlayer.pauseVideo();
      } else {
        currentPlayer.playVideo();
      }
      if (currentArticle) {
        // Show/focus the currently active song
        var headerHeight = $("header").outerHeight() || 70;
        var offset = currentArticle.offset().top - (headerHeight + 10);
        $("html, body").animate({ scrollTop: offset }, 250);
      }
    } else {
      var firstArticle = getSortedVisibleArticles().first();
      if (firstArticle.length) {
        playArticle(firstArticle);
      }
    }
  });

  $("#shuffle-btn").click(function () {
    $(this).toggleClass("active");
    isShuffle = $(this).hasClass("active");

    var isCurrentlyPlaying = false;
    if (currentPlayer) {
      try {
        var state = currentPlayer.getPlayerState();
        if (state === YT.PlayerState.PLAYING || state === YT.PlayerState.BUFFERING) {
          isCurrentlyPlaying = true;
        }
      } catch (e) {}
    }

    if (!isCurrentlyPlaying) {
      var visibleArticles = getSortedVisibleArticles();
      if (visibleArticles.length) {
        var randomIndex = Math.floor(Math.random() * visibleArticles.length);
        var randomArticle = visibleArticles.eq(randomIndex);
        playArticle(randomArticle);
      }
    } else {
      updatePlayerControls(true);
    }
  });

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
              currentArticle = $(player).closest("article");
              updatePlayerControls(true);
            } else if (event.data === YT.PlayerState.PAUSED) {
              if (currentPlayer === ytPlayer) {
                updatePlayerControls(false);
              }
            } else if (event.data === YT.PlayerState.ENDED) {
              if (currentPlayer === ytPlayer) {
                playNextTrack();
              }
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
      $(player).data("ytPlayer", ytPlayer);
    });
  });

  function populateAlbumsTOC() {
    var tocList = $("#albums-toc-list");
    tocList.empty();

    var visibleArticles = getSortedVisibleArticles();
    if (visibleArticles.length === 0) {
      tocList.append('<div style="padding: 10px; color: #888; font-size: 11px; font-family: monospace;">No matching albums</div>');
      return;
    }

    visibleArticles.each(function (index) {
      var art = $(this);
      var title = art.find("header h2").text().trim();
      var artist = art.find("header h3:contains('By:')").text().replace("By:", "").trim();
      var yearStr = art.find("header h3:contains('Released:')").text();
      var match = yearStr.match(/\d{4}/);
      var year = match ? match[0] : "";

      var id = art.attr("id");
      if (!id) {
        id = "album-" + title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
        art.attr("id", id);
      }

      var text = artist + ' - ' + title;
      if (year) {
        text += ' (' + year + ')';
      }

      var tocItem = $('<a href="#' + id + '" class="toc-item">' + text + '</a>');
      tocList.append(tocItem);
    });
  }
});
