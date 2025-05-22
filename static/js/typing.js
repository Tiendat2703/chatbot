function typeWriterEffectWithHTML(targetElement, htmlString, speed = 30, chatBox = null) {
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = htmlString;

    function typeNode(node, parent) {
        return new Promise((resolve) => {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                let i = 0;
                const span = document.createElement("span");
                parent.appendChild(span);
                const interval = setInterval(() => {
                    if (i < text.length) {
                        span.textContent += text[i++];
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: "smooth"
                        });
                    } else {
                        clearInterval(interval);
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: "smooth"
                        });
                        resolve();
                    }
                }, speed);
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                const el = document.createElement(node.tagName);
                for (let attr of node.attributes) {
                    el.setAttribute(attr.name, attr.value);
                }
                parent.appendChild(el);

                const children = Array.from(node.childNodes);
                let p = Promise.resolve();
                for (let child of children) {
                    p = p.then(() => typeNode(child, el));
                }
                p.then(resolve);
            } else {
                resolve();
            }
        });
    }

    const children = Array.from(tempDiv.childNodes);
    let chain = Promise.resolve();
    for (let child of children) {
        chain = chain.then(() => typeNode(child, targetElement));
    }
    return chain; // Thêm dòng này để trả về Promise
}