from app import app

if __name__ == "__main__":
    client = app.test_client()
    resp = client.get("/api/timeline")
    print(resp.status_code)
    print(resp.is_json)
    js = resp.get_json()
    print("keys", sorted(js.keys()))
    items = js.get("items", [])
    print("num_years", len(items))
    if items:
        sample = items[0]
        print("year", sample.get("year"))
        print("left months", len(sample.get("left", {}).get("months", [])))
        print("right months", len(sample.get("right", {}).get("months", [])))
        if sample.get("left", {}).get("months"):
            lm0 = sample["left"]["months"][0]
            print("left sample month", lm0.get("month"), "items", len(lm0.get("items", [])))
            if lm0.get("items"):
                print(
                    "left item example",
                    {
                        k: lm0["items"][0][k]
                        for k in ["displayDate", "company", "title", "status"]
                        if k in lm0["items"][0]
                    },
                )
        if sample.get("right", {}).get("months"):
            rm0 = sample["right"]["months"][0]
            print("right sample month", rm0.get("month"), "items", len(rm0.get("items", [])))
            if rm0.get("items"):
                print(
                    "right item example",
                    {k: rm0["items"][0][k] for k in ["displayDate", "company", "title"] if k in rm0["items"][0]},
                )
