// Setup and interaction handlers for Jazz Fuzz site
$(document).ready(function () {
  // Collapse details handler
  $("#collapse-main").click(function () {
    $(this).toggleClass("inverted");
    $("main").slideToggle("slow");
  });

  // Sort by artist handler
  $("#sort-artist-button").click(function () {
    $(this).addClass("inverted");
    $("#sort-year-button").removeClass("inverted");
    var posts = $("#posts").children("article");
    posts.sort(function (a, b) {
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
    });
    $("#posts").empty().append(posts);
  });

  // Sort by year handler
  $("#sort-year-button").click(function () {
    $(this).addClass("inverted");
    $("#sort-artist-button").removeClass("inverted");
    var posts = $("#posts").children("article");
    posts.sort(function (a, b) {
      var yearAStr = $(a).find("header h3:contains('Released:')").text();
      var yearBStr = $(b).find("header h3:contains('Released:')").text();
      var matchA = yearAStr.match(/\d{4}/);
      var matchB = yearBStr.match(/\d{4}/);
      var yearA = matchA ? parseInt(matchA[0], 10) : 0;
      var yearB = matchB ? parseInt(matchB[0], 10) : 0;
      return yearA - yearB;
    });
    $("#posts").empty().append(posts);
  });

  // Trigger default state on page load
  $("#sort-year-button").trigger("click");

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
