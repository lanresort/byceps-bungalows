onDomReady(() => {
  const bodyElem = document.querySelector('body');
  document.querySelectorAll('.bungalow-map area').forEach(function(areaElem) {
    const tipWrapperElem = document.createElement('div');
    tipWrapperElem.innerHTML = areaElem.getAttribute('data-tip');

    const tipElem = tipWrapperElem.querySelector('.bungalow-tip');
    bodyElem.appendChild(tipElem);

    areaElem.setAttribute('display', 'outline: 1px solid red');

    areaElem.addEventListener('mouseover', function() {
      tipElem.classList.add('visible');
    });

    areaElem.addEventListener('mousemove', function(event) {
      tipElem.setAttribute('style', 'left: ' + event.pageX + 'px; top: ' + event.pageY + 'px;');
    });

    areaElem.addEventListener('mouseout', function() {
      tipElem.classList.remove('visible');
    });
  });
});
