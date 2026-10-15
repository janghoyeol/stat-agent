const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const statusEl = document.getElementById("status");
const traceEl = document.getElementById("trace");
const answerEl = document.getElementById("answer");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  statusEl.textContent = "조회 중...";
  statusEl.classList.remove("error");
  traceEl.innerHTML = "";
  answerEl.textContent = "";
  form.querySelector("button").disabled = true;

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const data = await res.json();
    renderTrace(data.trace || []);
    answerEl.textContent = data.answer || "(답변 없음)";
    statusEl.textContent = `도구 호출 ${data.trace?.length ?? 0}번`;
  } catch (err) {
    statusEl.textContent = `에러: ${err.message}`;
    statusEl.classList.add("error");
  } finally {
    form.querySelector("button").disabled = false;
  }
});

function renderTrace(trace) {
  for (const step of trace) {
    const details = document.createElement("details");
    details.className = "step" + (step.is_error ? " error" : "");

    const summary = document.createElement("summary");
    summary.textContent = `${step.tool}(${JSON.stringify(step.input)})`;
    details.appendChild(summary);

    const pre = document.createElement("pre");
    pre.textContent = typeof step.output === "string" ? step.output : JSON.stringify(step.output, null, 2);
    details.appendChild(pre);

    traceEl.appendChild(details);
  }
}
